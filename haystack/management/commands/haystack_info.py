from django.core.management.base import BaseCommand

from haystack import connections
from haystack.constants import DEFAULT_ALIAS


class Command(BaseCommand):
    help = "Provides feedback about the current Haystack setup."  # noqa A003

    def handle(self, **options):
        """Provides feedback about the current Haystack setup."""

        unified_index = connections[DEFAULT_ALIAS].get_unified_index()
        indexed = unified_index.get_indexed_models()
        index_count = len(indexed)
        self.stdout.write("Number of handled %s index(es)." % index_count)

        for index in indexed:
            self.stdout.write(
                "  - Model: %s by Index: %s"
                % (index.__name__, unified_index.get_indexes()[index])
            )
