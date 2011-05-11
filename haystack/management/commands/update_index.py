import datetime
from optparse import make_option
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import AppCommand
from django.db import reset_queries
from django.utils.encoding import smart_str
from haystack import connections, connection_router
from haystack.constants import DEFAULT_ALIAS
from haystack.query import SearchQuerySet


DEFAULT_BATCH_SIZE = None
DEFAULT_AGE = None


class Command(AppCommand):
    help = "Freshens the index for the given app(s)."
    base_options = (
        make_option('-a', '--age', action='store', dest='age',
            default=DEFAULT_AGE, type='int',
            help='Number of hours back to consider objects new.'
        ),
        make_option('-b', '--batch-size', action='store', dest='batchsize',
            default=None, type='int',
            help='Number of items to index at once.'
        ),
        make_option('-r', '--remove', action='store_true', dest='remove',
            default=False, help='Remove objects from the index that are no longer present in the database.'
        ),
        make_option("-u", "--using", action="store", type="string", dest="using", default=None,
            help='If provided, chooses a connection to work with.'
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
        self.age = options.get('age', DEFAULT_AGE)
        self.remove = options.get('remove', False)
        self.using = options.get('using') or DEFAULT_ALIAS
        
        self.backend = connections[self.using].get_backend()
        
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
        from haystack.exceptions import NotHandled
        
        unified_index = connections[self.using].get_unified_index()
        
        for model in get_models(app):
            try:
                index = unified_index.get_index(model)
            except NotHandled:
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
            
            if not hasattr(index.index_queryset(), 'filter'):
                raise ImproperlyConfigured("The '%r' class must return a 'QuerySet' in the 'get_queryset' method." % index)
            
            # `.select_related()` seems like a good idea here but can fail on
            # nullable `ForeignKey` as well as what seems like other cases.
            qs = index.index_queryset().filter(**extra_lookup_kwargs).order_by(model._meta.pk.name)
            total = qs.count()
            
            if self.verbosity >= 1:
                print "Indexing %d %s." % (total, smart_str(model._meta.verbose_name_plural))
            
            pks_seen = set()
            
            for start in range(0, total, self.backend.batch_size):
                end = min(start + self.backend.batch_size, total)
                
                # Get a clone of the QuerySet so that the cache doesn't bloat up
                # in memory. Useful when reindexing large amounts of data.
                small_cache_qs = qs.all()
                current_qs = small_cache_qs[start:end]
                
                for obj in current_qs:
                    pks_seen.add(smart_str(obj.pk))
                
                if self.verbosity >= 2:
                    print "  indexing %s - %d of %d." % (start+1, end, total)
                
                self.backend.update(index, current_qs)
                
                # Clear out the DB connections queries because it bloats up RAM.
                reset_queries()
            
            if self.remove:
                if self.age or total <= 0:
                    # They're using a reduced set, which may not incorporate
                    # all pks. Rebuild the list with everything.
                    pks_seen = set()
                    qs = index.index_queryset().values_list('pk', flat=True)
                    total = qs.count()
                    
                    for pk in qs:
                        pks_seen.add(smart_str(pk))
                
                for start in range(0, total, self.backend.batch_size):
                    upper_bound = start + self.backend.batch_size
                    
                    # Fetch a list of results.
                    # Can't do pk range, because id's are strings (thanks comments
                    # & UUIDs!).
                    stuff_in_the_index = SearchQuerySet().models(model)[start:upper_bound]
                    
                    # Iterate over those results.
                    for result in stuff_in_the_index:
                        # Be careful not to hit the DB.
                        if not smart_str(result.pk) in pks_seen:
                            # The id is NOT in the small_cache_qs, issue a delete.
                            if self.verbosity >= 2:
                                print "  removing %s." % result.pk
                            
                            self.backend.remove(".".join([result.app_label, result.model_name, str(result.pk)]))
