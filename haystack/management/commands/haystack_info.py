from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Provides feedback about the current Haystack setup."
    
    def handle_noargs(self, **options):
        """Provides feedback about the current Haystack setup."""
        # Cause the default site to load.
        from haystack import site
        
        indexed = site.get_indexed_models()
        index_count = len(indexed)
        print "Loaded URLconf to initialize SearchSite..."
        print "Main site registered %s index(es)." % index_count
        
        for index in indexed:
            print "  - %s" % index
