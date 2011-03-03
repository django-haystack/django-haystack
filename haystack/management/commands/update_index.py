import datetime
from optparse import make_option
from django.conf import settings
from django.core.management.base import AppCommand, CommandError
from django.db import reset_queries
from django.utils.encoding import smart_str
from haystack.query import SearchQuerySet
try:
    from django.utils import importlib
except ImportError:
    from haystack.utils import importlib
try:
    set
except NameError:
    from sets import Set as set


DEFAULT_BATCH_SIZE = getattr(settings, 'HAYSTACK_BATCH_SIZE', 1000)
DEFAULT_AGE = None


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
        # Cause the default site to load.
        from haystack import site
        from django.db.models import get_models
        from haystack.exceptions import NotRegistered
        
        if self.site:
            path_bits = self.site.split('.')
            module_name = '.'.join(path_bits[:-1])
            site_name = path_bits[-1]
            
            try:
                module = importlib.import_module(module_name)
                site = getattr(module, site_name)
            except (ImportError, NameError):
                pass
        
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
            
            # `.select_related()` seems like a good idea here but can fail on
            # nullable `ForeignKey` as well as what seems like other cases.
            qs = index.get_queryset().filter(**extra_lookup_kwargs).order_by(model._meta.pk.name)
            total = qs.count()
            
            if self.verbosity >= 1:
                print "Indexing %d %s." % (total, smart_str(model._meta.verbose_name_plural))
            
            pks_seen = set()
            
            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                
                # Get a clone of the QuerySet so that the cache doesn't bloat up
                # in memory. Useful when reindexing large amounts of data.
                small_cache_qs = qs.all()
                current_qs = small_cache_qs[start:end]
                
                for obj in current_qs:
                    pks_seen.add(smart_str(obj.pk))
                
                if self.verbosity >= 2:
                    print "  indexing %s - %d of %d." % (start+1, end, total)
                
                index.backend.update(index, current_qs)
                
                # Clear out the DB connections queries because it bloats up RAM.
                reset_queries()
            
            if self.remove:
                if self.age or total <= 0:
                    # They're using a reduced set, which may not incorporate
                    # all pks. Rebuild the list with everything.
                    pks_seen = set()
                    qs = index.get_queryset().values_list('pk', flat=True)
                    total = qs.count()
                    
                    for pk in qs:
                        pks_seen.add(smart_str(pk))
                
                for start in range(0, total, self.batchsize):
                    upper_bound = start + self.batchsize
                    
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
                            
                            index.backend.remove(".".join([result.app_label, result.model_name, str(result.pk)]))
