from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from haystack.management.commands.clear_index import Command as ClearCommand
from haystack.management.commands.update_index import Command as UpdateCommand
from optparse import make_option

class Command(BaseCommand):
    help = "Completely rebuilds the search index by removing the old data and then updating."
    base_options = (
        make_option("-s", "--site", action="store", type="string", dest="site",
            help='If provided, configures Haystack to use the appropriate site module. (Defaults to `haystack.site`)',
        ),
    )
    option_list = BaseCommand.option_list + ClearCommand.base_options + UpdateCommand.base_options + base_options
    
    def handle(self, **options):
        call_command('clear_index', **options)
        call_command('update_index', **options)
