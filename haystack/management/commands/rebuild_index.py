# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management import call_command
from django.core.management.base import BaseCommand

from haystack.management.commands.clear_index import Command as ClearCommand
from haystack.management.commands.update_index import Command as UpdateCommand

__all__ = ['Command']

_combined_options = list(BaseCommand.option_list)
_combined_options.extend(option for option in UpdateCommand.base_options
                         if option.get_opt_string() not in [i.get_opt_string() for i in _combined_options])
_combined_options.extend(option for option in ClearCommand.base_options
                         if option.get_opt_string() not in [i.get_opt_string() for i in _combined_options])


class Command(BaseCommand):
    help = "Completely rebuilds the search index by removing the old data and then updating."
    option_list = _combined_options

    def handle(self, **options):
        call_command('clear_index', **options)
        call_command('update_index', **options)
