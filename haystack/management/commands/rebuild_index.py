from django.conf import settings
from django.core.management import call_command
from django.core.management.base import NoArgsCommand, CommandError


class Command(NoArgsCommand):
    help = "Completely rebuilds the search index by removing the old data and then updating."
    
    def handle_noargs(self, **options):
        call_command('clear_index')
        call_command('update_index')
