import datetime
from optparse import make_option
from django.core.management.base import AppCommand, CommandError
from django.utils.encoding import smart_str


DEFAULT_BATCH_SIZE = 1000
DEFAULT_AGE = None


class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('-a', '--age', action='store', dest='age',
            default=DEFAULT_AGE, type='int',
            help='Number of hours back to consider objects new.'
        ),
        make_option('-b', '--batch-size', action='store', dest='batchsize', 
            default=DEFAULT_BATCH_SIZE, type='int',
            help='Number of items to index at once.'
        ),
        # make_option('--verbosity', action='store', dest='verbosity', default='1',
        #     type='choice', choices=['0', '1', '2'],
        #     help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'
        # ),
    )
    help = "Reindex the given app(s)."

    def handle(self, *apps, **options):
        self.verbosity = int(options.get('verbosity', 1))
        self.batchsize = options.get('batchsize', DEFAULT_BATCH_SIZE)
        self.age = options.get('age', DEFAULT_AGE)
        
        if not apps:
            self.handle_app(None, **options)
        else:
            return super(Command, self).handle(*apps, **options)

    def handle_app(self, app, **options):
        # Cause the default site to load.
        from haystack import handle_registrations
        handle_registrations()
        
        from django.db.models import get_models
        from haystack.sites import site, NotRegistered

        for model in get_models(app):
            try:
                index = site.get_index(model)
            except NotRegistered:
                if self.verbosity >= 2:
                    print "Skipping '%s' - no index." % model
                continue

            extra_lookup_kwargs = {}
            updated_field = index.get_updated_field()
            
            if self.age:
                if updated_field:
                    extra_lookup_kwargs['%s__gte' % updated_field] = datetime.datetime.now() - datetime.timedelta(hours=self.age)
                else:
                    if self.verbosity >= 2:
                        print "No updated date field found for '%s' - not restricting by age." % model.__name__
            
            # DRL_TODO: .select_related() seems like a good idea here but
            #           can cause empty QuerySets. Why?
            qs = index.get_query_set().filter(**extra_lookup_kwargs).order_by(model._meta.pk.name)
            total = qs.count()

            if self.verbosity >= 1:
                print "Indexing %d %s." % (total, smart_str(model._meta.verbose_name_plural))

            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                
                if self.verbosity >= 2:
                    print "  indexing %s - %d of %d." % (start+1, end, total)
                
                # Get a clone of the QuerySet so that the cache doesn't bloat up
                # in memory. Useful when reindexing large amounts of data.
                small_cache_qs = qs.all()
                index.backend.update(index, small_cache_qs[start:end])
