# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from optparse import make_option

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.template import Context, loader


from haystack import constants
from haystack.backends.solr_backend import SolrSearchBackend
from haystack.exceptions import SearchBackendError

class Command(BaseCommand):
    help = "Generates a Solr schema that reflects the indexes."
    base_options = (
        make_option("-f", "--filename", action="store", type="string", dest="filename",
                help='For Solr version before 5.0.0. If provided, directs output to a XML schema.'),
        make_option("-s", "--stdout", action="store_true", dest="stdout",
            help='For Solr version before 5.0.0, print the schema.xml to stdout', default=False),
        make_option("-u", "--using", action="store", type="string", dest="using", default=constants.DEFAULT_ALIAS,
                    help='If provided, chooses a connection to work with.'),
    )
    option_list = BaseCommand.option_list + base_options

    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        from haystack import connections

        using = options.get('using')
        backend = connections[using].get_backend()

        if not isinstance(backend, SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine)." % backend.connection_alias)

        if options.get('filename') or options.get('stdout'):
            schema_xml = self.build_template(using=using)
            if options.get('filename'):
                self.write_file(options.get('filename'), schema_xml)
            else:
                self.print_schema(schema_xml)
            return

        content_field_name, fields = backend.build_schema(connections[using].get_unified_index().all_searchfields())

        django_fields = [
            dict(name=constants.ID, type="string", indexed="true", stored="true", multiValued="false", required="true"),
            dict(name= constants.DJANGO_CT, type="string", indexed="true", stored="true", multiValued="false"),
            dict(name= constants.DJANGO_ID, type="string", indexed="true", stored="true", multiValued="false"),
            dict(name="_version_", type="long", indexed="true", stored ="true"),
        ]

        admin = backend.schema_admin
        for field in fields + django_fields:
            resp = admin.add_field(field)
            self.log(field, resp, backend)

    def build_context(self, using):
        from haystack import connections
        backend = connections[using].get_backend()

        if not isinstance(backend, SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine)." % backend.connection_alias)

        content_field_name, fields = backend.build_schema(connections[using].get_unified_index().all_searchfields())
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

    def write_file(self, filename, schema_xml):
        schema_file = open(filename, 'w')
        schema_file.write(schema_xml)
        schema_file.close()

    def print_schema(self, schema_xml):
        self.stderr.write("--------------------------------------------------------------------------------------------")
        self.stderr.write("Save the following output to 'schema.xml' and place it in your Solr configuration directory.")
        self.stderr.write("--------------------------------------------------------------------------------------------")
        self.stdout.write(schema_xml)

    def log(self, field, response, backend):
        try:
            message = response.json()
        except ValueError as exc:
            self.stderr.write('Unable to decode response from Solr: %s' % exc)
            raise SearchBackendError('Unable to decode response from Solr')

        if 'errors' in message:
            self.stdout.write("%s." % [" ".join(err.get('errorMessages')) for err in message['errors']])
        elif 'responseHeader' in message and 'status' in message['responseHeader']:
            sys.stdout.write("Successfully created the field %s" % field['name'])
        else:
            sys.stdout.write("%s" % message)
