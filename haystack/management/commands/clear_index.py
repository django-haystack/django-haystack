import sys
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Clears out the search index completely."
    
    def handle_noargs(self, **options):
        """Clears out the search index completely."""
        # Cause the default site to load.
        from haystack import site
        
        print
        print "WARNING: This will irreparably remove EVERYTHING from your search index."
        print "Your choices after this are to restore from backups or rebuild via the `rebuild_index` command."
        
        yes_or_no = raw_input("Are you sure you wish to continue? [y/N] ")
        print
        
        if not yes_or_no.lower().startswith('y'):
            print "No action taken."
            sys.exit()
        
        print "Removing all documents from your index because you said so."
        
        from haystack import backend
        sb = backend.SearchBackend()
        sb.clear()
        
        print "All documents removed."
