import datetime
import os
import warnings
from optparse import make_option
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import AppCommand
from django.db import reset_queries
from django.utils.encoding import smart_str
from haystack.query import SearchQuerySet
try:
    from django.utils import importlib
except ImportError:
    from haystack.utils import importlib


DEFAULT_BATCH_SIZE = getattr(settings, 'HAYSTACK_BATCH_SIZE', 1000)
DEFAULT_AGE = None


def worker(bits):
    # We need to reset the connections, otherwise the different processes
    # will try to share the connection, which causes things to blow up.
    from django.db import connections
    
    for alias, info in connections.databases.items():
        # We need to also tread lightly with SQLite, because blindly wiping
        # out connections (via ``... = {}``) destroys in-memory DBs.
        if not 'sqlite3' in info['ENGINE']:
            try:
                del(connections._connections[alias])
            except KeyError:
                pass
    
    if bits[0] == 'do_update':
        func, model, start, end, total, optional_site, age, verbosity = bits
    elif bits[0] == 'do_remove':
        func, model, pks_seen, start, upper_bound, optional_site, verbosity = bits
    else:
        return
    
    site = get_site(optional_site)
    index = site.get_index(model)
    
    if func == 'do_update':
        qs = build_queryset(index, model, age=age, verbosity=verbosity)
        do_update(index, qs, start, end, total, verbosity=verbosity)
    elif bits[0] == 'do_remove':
        do_remove(index, model, pks_seen, start, upper_bound, verbosity=verbosity)


def get_site(optional_site=None):
    # Cause the default site to load.
    from haystack import site
    
    if optional_site:
        path_bits = optional_site.split('.')
        module_name = '.'.join(path_bits[:-1])
        site_name = path_bits[-1]
        
        try:
            module = importlib.import_module(module_name)
            site = getattr(module, site_name)
        except (ImportError, NameError):
            pass
    
    return site


def build_queryset(index, model, age=DEFAULT_AGE, verbosity=1):
    extra_lookup_kwargs = {}
    updated_field = index.get_updated_field()
    
    if age:
        if updated_field:
            extra_lookup_kwargs['%s__gte' % updated_field] = datetime.datetime.now() - datetime.timedelta(hours=age)
        else:
            if verbosity >= 2:
                print "No updated date field found for '%s' - not restricting by age." % model.__name__
    
    index_qs = None

    if hasattr(index, 'get_queryset'):
        warnings.warn("'SearchIndex.get_queryset' is pending deprecation & will be removed in Haystack v2. Please rename them to 'index_queryset'.")
        index_qs = index.get_queryset()
    else:
        index_qs = index.index_queryset()

    if not hasattr(index_qs, 'filter'):
        raise ImproperlyConfigured("The '%r' class must return a 'QuerySet' in the 'index_queryset' method." % index)
    
    # `.select_related()` seems like a good idea here but can fail on
    # nullable `ForeignKey` as well as what seems like other cases.
    return index_qs.filter(**extra_lookup_kwargs).order_by(model._meta.pk.name)


def do_update(index, qs, start, end, total, verbosity=1):
    # Get a clone of the QuerySet so that the cache doesn't bloat up
    # in memory. Useful when reindexing large amounts of data.
    small_cache_qs = qs.all()
    current_qs = small_cache_qs[start:end]
    
    if verbosity >= 2:
        if os.getpid() == os.getppid():
            print "  indexed %s - %d of %d." % (start+1, end, total)
        else:
            print "  indexed %s - %d of %d (by %s)." % (start+1, end, total, os.getpid())
    
    index.backend.update(index, current_qs)
    
    # Clear out the DB connections queries because it bloats up RAM.
    reset_queries()


def do_remove(index, model, pks_seen, start, upper_bound, verbosity=1):
    # Fetch a list of results.
    # Can't do pk range, because id's are strings (thanks comments
    # & UUIDs!).
    stuff_in_the_index = SearchQuerySet().models(model)[start:upper_bound]
    
    # Iterate over those results.
    for result in stuff_in_the_index:
        # Be careful not to hit the DB.
        if not smart_str(result.pk) in pks_seen:
            # The id is NOT in the small_cache_qs, issue a delete.
            if verbosity >= 2:
                print "  removing %s." % result.pk
            
            index.backend.remove(".".join([result.app_label, result.model_name, str(result.pk)]))


class Command(AppCommand):
    help = "Freshens the index for the given app(s)."
    base_options = (
        make_option('-a', '--age', action='store', dest='age',
            default=DEFAULT_AGE, type='int',
            help='Number of hours back to consider objects new.'
        ),
        make_option('-b', '--batch-size', action='store', dest='batchsize',
            default=DEFAULT_BATCH_SIZE, type='int',
            help='Number of items to index at once.'
        ),
        make_option('-s', '--site', action='store', dest='site',
            type='string', help='The site object to use when reindexing (like `search_sites.mysite`).'
        ),
        make_option('-r', '--remove', action='store_true', dest='remove',
            default=False, help='Remove objects from the index that are no longer present in the database.'
        ),
        make_option('-k', '--workers', action='store', dest='workers',
            default=0, type='int', 
            help='Allows for the use multiple workers to parallelize indexing. Requires multiprocessing.'
        ),
    )
    option_list = AppCommand.option_list + base_options
    
    # Django 1.0.X compatibility.
    verbosity_present = False
    
    for option in option_list:
        if option.get_opt_string() == '--verbosity':
            verbosity_present = True
    
    if verbosity_present is False:
        option_list = option_list + (
            make_option('--verbosity', action='store', dest='verbosity', default='1',
                type='choice', choices=['0', '1', '2'],
                help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'
            ),
        )
    
    def handle(self, *apps, **options):
        self.verbosity = int(options.get('verbosity', 1))
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE)
        self.age = options.get('age', DEFAULT_AGE)
        self.site = options.get('site')
        self.remove = options.get('remove', False)
        self.workers = int(options.get('workers', 0))
        
        if not apps:
            from django.db.models import get_app
            # Do all, in an INSTALLED_APPS sorted order.
            apps = []
            
            for app in settings.INSTALLED_APPS:
                try:
                    app_label = app.split('.')[-1]
                    loaded_app = get_app(app_label)
                    apps.append(app_label)
                except:
                    # No models, no problem.
                    pass
            
        return super(Command, self).handle(*apps, **options)
    
    def handle_app(self, app, **options):
        from django.db.models import get_models
        from haystack.exceptions import NotRegistered
        
        site = get_site(self.site)
        
        if self.workers > 0:
            import multiprocessing
        
        for model in get_models(app):
            try:
                index = site.get_index(model)
                # Manually set the ``site`` on the backend to the correct one.
                index.backend.site = site
            except NotRegistered:
                if self.verbosity >= 2:
                    print "Skipping '%s' - no index." % model
                continue
                
            qs = build_queryset(index, model, age=self.age, verbosity=self.verbosity)
            total = qs.count()
            
            if self.verbosity >= 1:
                print "Indexing %d %s." % (total, smart_str(model._meta.verbose_name_plural))
            
            pks_seen = set([smart_str(pk) for pk in qs.values_list('pk', flat=True)])
            
            if self.workers > 0:
                ghetto_queue = []
            
            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                
                if self.workers == 0:
                    do_update(index, qs, start, end, total, self.verbosity)
                else:
                    ghetto_queue.append(('do_update', model, start, end, total, self.site, self.age, self.verbosity))
            
            if self.workers > 0:
                pool = multiprocessing.Pool(self.workers)
                pool.map(worker, ghetto_queue)
            
            if self.remove:
                if self.age or total <= 0:
                    # They're using a reduced set, which may not incorporate
                    # all pks. Rebuild the list with everything.
                    qs = index.index_queryset().values_list('pk', flat=True)
                    pks_seen = set([smart_str(pk) for pk in qs])
                    total = len(pks_seen)
                
                if self.workers > 0:
                    ghetto_queue = []
                
                for start in range(0, total, self.batchsize):
                    upper_bound = start + self.batchsize
                    
                    if self.workers == 0:
                        do_remove(index, model, pks_seen, start, upper_bound)
                    else:
                        ghetto_queue.append(('do_remove', model, pks_seen, start, upper_bound, self.site, self.verbosity))
                
                if self.workers > 0:
                    pool = multiprocessing.Pool(self.workers)
                    pool.map(worker, ghetto_queue)
