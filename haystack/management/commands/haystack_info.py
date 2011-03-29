from django.core.management.base import NoArgsCommand
from django.core.management.base import BaseCommand
from optparse import make_option
try:
    from django.utils import importlib
except ImportError:
    from haystack.utils import importlib

class Command(NoArgsCommand):
    help = "Provides feedback about the current Haystack setup."
    base_options = (
        make_option("-s", "--site", action="store", type="string", dest="site",
            help='If provided, configures Haystack to use the appropriate site module. (Defaults to `haystack.site`)',
        ),
    )
    option_list = BaseCommand.option_list + base_options
    
    def handle_noargs(self, **options):
        """Provides feedback about the current Haystack setup."""
        if options.get('site'):
            mod_name, attr_name = options['site'].rsplit('.', 1)
            self.site = getattr(importlib.import_module(mod_name), attr_name)
        else:
            from haystack import site
            self.site = site
        
        indexed = self.site.get_indexed_models()
        index_count = len(indexed)
        print "Loaded URLconf to initialize SearchSite..."
        print "Main site registered %s index(es)." % index_count
        
        for index in indexed:
            print "  - %s" % index
