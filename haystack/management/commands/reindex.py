import datetime
from optparse import make_option
from django.conf import settings
from django.core.management.base import AppCommand, CommandError
from django.db import reset_queries
from django.utils.encoding import smart_str


DEFAULT_BATCH_SIZE = getattr(settings, 'HAYSTACK_BATCH_SIZE', 1000)
DEFAULT_AGE = None


class Command(AppCommand):
    help = "Reindex the given app(s)."
    option_list = AppCommand.option_list + (
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
    )
    
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
        
        if not apps:
            self.handle_app(None, **options)
        else:
            return super(Command, self).handle(*apps, **options)
    
    def handle_app(self, app, **options):
        # Cause the default site to load.
        from haystack import handle_registrations
        handle_registrations()
        
        from django.db.models import get_models
        from haystack.exceptions import NotRegistered
        
        if self.site:
            path_bits = self.site.split('.')
            module_name = '.'.join(path_bits[:-1])
            site_name = path_bits[-1]
            
            try:
                module = __import__(module_name, {}, {}, [''])
                site = getattr(module, site_name)
            except (ImportError, NameError):
                # Fall back to the main site.
                from haystack import site
        else:
            from haystack import site
        
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
            
            for start in range(0, total, self.batchsize):
                end = min(start + self.batchsize, total)
                
                if self.verbosity >= 2:
                    print "  indexing %s - %d of %d." % (start+1, end, total)
                
                # Get a clone of the QuerySet so that the cache doesn't bloat up
                # in memory. Useful when reindexing large amounts of data.
                small_cache_qs = qs.all()
                index.backend.update(index, small_cache_qs[start:end])
                
                # Clear out the DB connections queries because it bloats up RAM.
                reset_queries()
