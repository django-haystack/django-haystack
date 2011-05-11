from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from haystack.management.commands.clear_index import Command as ClearCommand
from haystack.management.commands.update_index import Command as UpdateCommand


class Command(BaseCommand):
    help = "Completely rebuilds the search index by removing the old data and then updating."
    option_list = list(BaseCommand.option_list) + list(ClearCommand.base_options) + [option for option in UpdateCommand.base_options if option.get_opt_string() == '-u']
    
    def handle(self, **options):
        call_command('clear_index', **options)
        call_command('update_index', **options)
