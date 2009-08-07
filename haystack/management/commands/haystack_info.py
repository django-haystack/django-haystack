from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Provides feedback about the current Haystack setup."
    
    def handle_noargs(self, **options):
        """Provides feedback about the current Haystack setup."""
        # Cause the default site to load.
        from haystack import site
        
        index_count = len(site.get_indexed_models())
        print "Loaded URLconf to initialize SearchSite..."
        print "Main site registered %s index(es)." % index_count
