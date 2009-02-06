from optparse import make_option
from django.core.management.base import AppCommand, CommandError
from django.utils.encoding import smart_str

DEFAULT_BATCH_SIZE = 1000

class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('-b', '--batch-size', action='store', dest='batchsize', 
            default=DEFAULT_BATCH_SIZE, type='int',
            help='Number of items to index at once.'
        ),
        # make_option('--verbosity', action='store', dest='verbosity', default='1',
        #     type='choice', choices=['0', '1', '2'],
        #     help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'
        # ),
    )
    help = "Reindex the given app."

    def handle(self, *apps, **options):
        self.verbosity = int(options.get('verbosity', 1))
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE)
        if not apps:
            self.handle_app(None, **options)
        else:
            return super(Command, self).handle(*apps, **options)

    def handle_app(self, app, **options):
        # Cause the default site to load.
        from django.conf import settings
        __import__(settings.ROOT_URLCONF)
        
        from django.db.models import get_models
        from djangosearch.sites import site, NotRegistered

        for model in get_models(app):
            try:
                index = site.get_index(model)
            except NotRegistered:
                if self.verbosity >= 2:
                    print "Skipping '%s' - no index" % model.__name__
                continue

            # DRL_FIXME: Had .select_related() on the end but it broke my queryset. Strange.
            qs = index.get_query_set().order_by(model._meta.pk.attname)
            total = qs.count()

            # import pdb; pdb.set_trace()
            if self.verbosity >= 1:
                print "Indexing %d %s" % (total, smart_str(model._meta.verbose_name_plural))

            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                
                if self.verbosity >= 2:
                    print "  indexing %s - %d of %d" % (start+1, end, total)
                
                # Get a clone of the QuerySet so that the cache doesn't bloat up
                # in memory. Useful when reindexing large amounts of data.
                small_cache_qs = qs.all()
                index.backend.update(index, small_cache_qs[start:end])
