# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import multiprocessing
import os
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import close_old_connections, reset_queries
from django.utils.encoding import force_text, smart_bytes
from django.utils.timezone import now

from haystack import connections as haystack_connections
from haystack.exceptions import NotHandled
from haystack.query import SearchQuerySet
from haystack.utils.app_loading import haystack_get_models, haystack_load_apps

DEFAULT_BATCH_SIZE = None
DEFAULT_AGE = None
DEFAULT_MAX_RETRIES = 5

LOG = multiprocessing.log_to_stderr(level=logging.WARNING)


def update_worker(args):
    if len(args) != 10:
        LOG.error('update_worker received incorrect arguments: %r', args)
        raise ValueError('update_worker received incorrect arguments')

    model, start, end, total, using, start_date, end_date, verbosity, commit, max_retries = args

    # FIXME: confirm that this is still relevant with modern versions of Django:
    # We need to reset the connections, otherwise the different processes
    # will try to share the connection, which causes things to blow up.
    from django.db import connections

    for alias, info in connections.databases.items():
        # We need to also tread lightly with SQLite, because blindly wiping
        # out connections (via ``... = {}``) destroys in-memory DBs.
        if 'sqlite3' not in info['ENGINE']:
            try:
                close_old_connections()
                if isinstance(connections._connections, dict):
                    del connections._connections[alias]
                else:
                    delattr(connections._connections, alias)
            except KeyError:
                pass

    # Request that the connection clear out any transient sessions, file handles, etc.
    haystack_connections[using].reset_sessions()

    unified_index = haystack_connections[using].get_unified_index()
    index = unified_index.get_index(model)
    backend = haystack_connections[using].get_backend()

    qs = index.build_queryset(start_date=start_date, end_date=end_date)
    do_update(backend, index, qs, start, end, total, verbosity, commit, max_retries)
    return args


def do_update(backend, index, qs, start, end, total, verbosity=1, commit=True,
              max_retries=DEFAULT_MAX_RETRIES):

    # Get a clone of the QuerySet so that the cache doesn't bloat up
    # in memory. Useful when reindexing large amounts of data.
    small_cache_qs = qs.all()
    current_qs = small_cache_qs[start:end]

    is_parent_process = hasattr(os, 'getppid') and os.getpid() == os.getppid()

    if verbosity >= 2:
        if is_parent_process:
            print("  indexed %s - %d of %d." % (start + 1, end, total))
        else:
            print("  indexed %s - %d of %d (worker PID: %s)." % (start + 1, end, total, os.getpid()))

    retries = 0
    while retries < max_retries:
        try:
            # FIXME: Get the right backend.
            backend.update(index, current_qs, commit=commit)
            if verbosity >= 2 and retries:
                print('Completed indexing {} - {}, tried {}/{} times'.format(start + 1,
                                                                             end,
                                                                             retries + 1,
                                                                             max_retries))
            break
        except Exception as exc:
            # Catch all exceptions which do not normally trigger a system exit, excluding SystemExit and
            # KeyboardInterrupt. This avoids needing to import the backend-specific exception subclasses
            # from pysolr, elasticsearch, whoosh, requests, etc.
            retries += 1

            error_context = {'start': start + 1,
                             'end': end,
                             'retries': retries,
                             'max_retries': max_retries,
                             'pid': os.getpid(),
                             'exc': exc}

            error_msg = 'Failed indexing %(start)s - %(end)s (retry %(retries)s/%(max_retries)s): %(exc)s'
            if not is_parent_process:
                error_msg += ' (pid %(pid)s): %(exc)s'

            if retries >= max_retries:
                LOG.error(error_msg, error_context, exc_info=True)
                raise
            elif verbosity >= 2:
                LOG.warning(error_msg, error_context, exc_info=True)

            # If going to try again, sleep a bit before
            time.sleep(2 ** retries)

    # Clear out the DB connections queries because it bloats up RAM.
    reset_queries()


class Command(BaseCommand):
    help = "Freshens the index for the given app(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            'app_label', nargs='*',
            help='App label of an application to update the search index.'
        )
        parser.add_argument(
            '-a', '--age', type=int, default=DEFAULT_AGE,
            help='Number of hours back to consider objects new.'
        )
        parser.add_argument(
            '-s', '--start', dest='start_date',
            help='The start date for indexing within. Can be any dateutil-parsable string, recommended to be YYYY-MM-DDTHH:MM:SS.'
        )
        parser.add_argument(
            '-e', '--end', dest='end_date',
            help='The end date for indexing within. Can be any dateutil-parsable string, recommended to be YYYY-MM-DDTHH:MM:SS.'
        )
        parser.add_argument(
            '-b', '--batch-size', dest='batchsize', type=int,
            help='Number of items to index at once.'
        )
        parser.add_argument(
            '-r', '--remove', action='store_true', default=False,
            help='Remove objects from the index that are no longer present in the database.'
        )
        parser.add_argument(
            '-u', '--using', action='append', default=[],
            help='Update only the named backend (can be used multiple times). '
                 'By default all backends will be updated.'
        )
        parser.add_argument(
            '-k', '--workers', type=int, default=0,
            help='Allows for the use multiple workers to parallelize indexing.'
        )
        parser.add_argument(
            '--nocommit', action='store_false', dest='commit',
            default=True, help='Will pass commit=False to the backend.'
        )
        parser.add_argument(
            '-t', '--max-retries', action='store', dest='max_retries',
            type=int, default=DEFAULT_MAX_RETRIES,
            help='Maximum number of attempts to write to the backend when an error occurs.'
        )

    def handle(self, **options):
        self.verbosity = int(options.get('verbosity', 1))
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE)
        self.start_date = None
        self.end_date = None
        self.remove = options.get('remove', False)
        self.workers = options.get('workers', 0)
        self.commit = options.get('commit', True)
        self.max_retries = options.get('max_retries', DEFAULT_MAX_RETRIES)

        self.backends = options.get('using')
        if not self.backends:
            self.backends = haystack_connections.connections_info.keys()

        age = options.get('age', DEFAULT_AGE)
        start_date = options.get('start_date')
        end_date = options.get('end_date')

        if self.verbosity > 2:
            LOG.setLevel(logging.DEBUG)
        elif self.verbosity > 1:
            LOG.setLevel(logging.INFO)

        if age is not None:
            self.start_date = now() - timedelta(hours=int(age))

        if start_date is not None:
            from dateutil.parser import parse as dateutil_parse

            try:
                self.start_date = dateutil_parse(start_date)
            except ValueError:
                pass

        if end_date is not None:
            from dateutil.parser import parse as dateutil_parse

            try:
                self.end_date = dateutil_parse(end_date)
            except ValueError:
                pass

        labels = options.get('app_label') or haystack_load_apps()
        for label in labels:
            for using in self.backends:
                try:
                    self.update_backend(label, using)
                except:
                    LOG.exception("Error updating %s using %s ", label, using)
                    raise

    def update_backend(self, label, using):
        backend = haystack_connections[using].get_backend()
        unified_index = haystack_connections[using].get_unified_index()

        for model in haystack_get_models(label):
            try:
                index = unified_index.get_index(model)
            except NotHandled:
                if self.verbosity >= 2:
                    self.stdout.write("Skipping '%s' - no index." % model)
                continue

            if self.workers > 0:
                # workers resetting connections leads to references to models / connections getting
                # stale and having their connection disconnected from under them. Resetting before
                # the loop continues and it accesses the ORM makes it better.
                close_old_connections()

            qs = index.build_queryset(using=using, start_date=self.start_date,
                                      end_date=self.end_date)

            total = qs.count()

            if self.verbosity >= 1:
                self.stdout.write(u"Indexing %d %s" % (
                    total, force_text(model._meta.verbose_name_plural))
                )

            batch_size = self.batchsize or backend.batch_size

            if self.workers > 0:
                ghetto_queue = []

            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)

                if self.workers == 0:
                    do_update(backend, index, qs, start, end, total, verbosity=self.verbosity,
                              commit=self.commit, max_retries=self.max_retries)
                else:
                    ghetto_queue.append((model, start, end, total, using, self.start_date, self.end_date,
                                         self.verbosity, self.commit, self.max_retries))

            if self.workers > 0:
                pool = multiprocessing.Pool(self.workers)

                successful_tasks = pool.map(update_worker, ghetto_queue)

                if len(ghetto_queue) != len(successful_tasks):
                    self.stderr.write('Queued %d tasks but only %d completed' % (len(ghetto_queue),
                                                                                 len(successful_tasks)))
                    for i in ghetto_queue:
                        if i not in successful_tasks:
                            self.stderr.write('Incomplete task: %s' % repr(i))

                pool.close()
                pool.join()

            if self.remove:
                if self.start_date or self.end_date or total <= 0:
                    # They're using a reduced set, which may not incorporate
                    # all pks. Rebuild the list with everything.
                    qs = index.index_queryset().values_list('pk', flat=True)
                    database_pks = set(smart_bytes(pk) for pk in qs)

                    total = len(database_pks)
                else:
                    database_pks = set(smart_bytes(pk) for pk in qs.values_list('pk', flat=True))

                # Since records may still be in the search index but not the local database
                # we'll use that to create batches for processing.
                # See https://github.com/django-haystack/django-haystack/issues/1186
                index_total = SearchQuerySet(using=backend.connection_alias).models(model).count()

                # Retrieve PKs from the index. Note that this cannot be a numeric range query because although
                # pks are normally numeric they can be non-numeric UUIDs or other custom values. To reduce
                # load on the search engine, we only retrieve the pk field, which will be checked against the
                # full list obtained from the database, and the id field, which will be used to delete the
                # record should it be found to be stale.
                index_pks = SearchQuerySet(using=backend.connection_alias).models(model)
                index_pks = index_pks.values_list('pk', 'id')

                # We'll collect all of the record IDs which are no longer present in the database and delete
                # them after walking the entire index. This uses more memory than the incremental approach but
                # avoids needing the pagination logic below to account for both commit modes:
                stale_records = set()

                for start in range(0, index_total, batch_size):
                    upper_bound = start + batch_size

                    # If the database pk is no longer present, queue the index key for removal:
                    for pk, rec_id in index_pks[start:upper_bound]:
                        if smart_bytes(pk) not in database_pks:
                            stale_records.add(rec_id)

                if stale_records:
                    if self.verbosity >= 1:
                        self.stdout.write("  removing %d stale records." % len(stale_records))

                    for rec_id in stale_records:
                        # Since the PK was not in the database list, we'll delete the record from the search
                        # index:
                        if self.verbosity >= 2:
                            self.stdout.write("  removing %s." % rec_id)

                        backend.remove(rec_id, commit=self.commit)
