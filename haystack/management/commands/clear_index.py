from optparse import make_option
import sys
from django.core.management.base import BaseCommand
from haystack.constants import DEFAULT_ALIAS


class Command(BaseCommand):
    help = "Clears out the search index completely."
    base_options = (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='If provided, no prompts will be issued to the user and the data will be wiped out.'
        ),
        make_option("-u", "--using", action="store", type="string", dest="using", default=DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        ),
    )
    option_list = BaseCommand.option_list + base_options
    
    def handle(self, **options):
        """Clears out the search index completely."""
        from haystack import connections
        self.verbosity = int(options.get('verbosity', 1))
        self.using = options.get('using')
        
        if options.get('interactive', True):
            print
            print "WARNING: This will irreparably remove EVERYTHING from your search index in connection '%s'." % self.using
            print "Your choices after this are to restore from backups or rebuild via the `rebuild_index` command."
            
            yes_or_no = raw_input("Are you sure you wish to continue? [y/N] ")
            print
            
            if not yes_or_no.lower().startswith('y'):
                print "No action taken."
                sys.exit()
        
        if self.verbosity >= 1:
            print "Removing all documents from your index because you said so."
        
        backend = connections[self.using].get_backend()
        backend.clear()
        
        if self.verbosity >= 1:
            print "All documents removed."
