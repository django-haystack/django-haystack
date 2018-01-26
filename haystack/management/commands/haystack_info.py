# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management.base import BaseCommand

from haystack import connections


class Command(BaseCommand):
    help = "Provides feedback about the current Haystack setup."

    def handle(self, **options):
        """Provides feedback about the current Haystack setup."""

        unified_index = connections['default'].get_unified_index()
        indexed = unified_index.get_indexed_models()
        index_count = len(indexed)
        self.stdout.write("Number of handled %s index(es)." % index_count)

        for index in indexed:
            self.stdout.write("  - Model: %s by Index: %s" % (
                index.__name__, unified_index.get_indexes()[index])
            )
