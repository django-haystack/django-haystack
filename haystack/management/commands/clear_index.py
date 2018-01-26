# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management.base import BaseCommand
from django.utils import six

from haystack import connections


class Command(BaseCommand):
    help = "Clears out the search index completely."

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', action='store_false', dest='interactive', default=True,
            help='If provided, no prompts will be issued to the user and the data will be wiped out.'
        )
        parser.add_argument(
            "-u", "--using", action="append", default=[],
            help='Update only the named backend (can be used multiple times). '
                 'By default all backends will be updated.'
        )
        parser.add_argument(
            '--nocommit', action='store_false', dest='commit',
            default=True, help='Will pass commit=False to the backend.'
        )

    def handle(self, **options):
        """Clears out the search index completely."""
        self.verbosity = int(options.get('verbosity', 1))
        self.commit = options.get('commit', True)

        using = options.get('using')
        if not using:
            using = connections.connections_info.keys()

        if options.get('interactive', True):
            self.stdout.write("WARNING: This will irreparably remove EVERYTHING from your search index in connection '%s'." % "', '".join(using))
            self.stdout.write("Your choices after this are to restore from backups or rebuild via the `rebuild_index` command.")

            yes_or_no = six.moves.input("Are you sure you wish to continue? [y/N] ")

            if not yes_or_no.lower().startswith('y'):
                self.stdout.write("No action taken.")
                return

        if self.verbosity >= 1:
            self.stdout.write("Removing all documents from your index because you said so.")

        for backend_name in using:
            backend = connections[backend_name].get_backend()
            backend.clear(commit=self.commit)

        if self.verbosity >= 1:
            self.stdout.write("All documents removed.")
