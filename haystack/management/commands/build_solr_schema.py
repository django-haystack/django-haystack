# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.template import Context, loader

from haystack import connections, connection_router, constants
from haystack.backends.solr_backend import SolrSearchBackend


class Command(BaseCommand):
    help = "Generates a Solr schema that reflects the indexes."

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--filename",
            help='If provided, directs output to a file instead of stdout.'
        )
        parser.add_argument(
            "-u", "--using", default=constants.DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        )

    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        using = options.get('using')
        schema_xml = self.build_template(using=using)

        if options.get('filename'):
            self.write_file(options.get('filename'), schema_xml)
        else:
            self.print_stdout(schema_xml)

    def build_context(self, using):
        backend = connections[using].get_backend()

        if not isinstance(backend, SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine)." % backend.connection_alias)

        content_field_name, fields = backend.build_schema(
            connections[using].get_unified_index().all_searchfields()
        )
        return Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': constants.DEFAULT_OPERATOR,
            'ID': constants.ID,
            'DJANGO_CT': constants.DJANGO_CT,
            'DJANGO_ID': constants.DJANGO_ID,
        })

    def build_template(self, using):
        t = loader.get_template('search_configuration/solr.xml')
        c = self.build_context(using=using)
        return t.render(c)

    def print_stdout(self, schema_xml):
        self.stderr.write("\n")
        self.stderr.write("\n")
        self.stderr.write("\n")
        self.stderr.write("Save the following output to 'schema.xml' and place it in your Solr configuration directory.\n")
        self.stderr.write("--------------------------------------------------------------------------------------------\n")
        self.stderr.write("\n")
        self.stdout.write(schema_xml)

    def write_file(self, filename, schema_xml):
        with open(filename, 'w') as schema_file:
            schema_file.write(schema_xml)
