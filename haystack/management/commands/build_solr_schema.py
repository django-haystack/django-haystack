# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand,CommandError
from django.template import Context, loader
from django.conf import settings

from haystack import connections, connection_router, constants
from haystack.backends.solr_backend import SolrSearchBackend

import pysolr
import os
import traceback
import requests
class Command(BaseCommand):
    help = "Generates a Solr schema that reflects the indexes using templates under a django template dir 'search_configuration/*.xml'"
    schema_template_loc = 'search_configuration/schema.xml'
    solrcfg_template_loc = 'search_configuration/solrconfig.xml'

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--filename",
            help='If provided, directs output to a file instead of stdout.'
        )
        parser.add_argument(
            "-u", "--using", default=constants.DEFAULT_ALIAS,
            help='If provided, chooses a connection to work with.'
        )
        parser.add_argument(
            "-c", "--configure_dir",
            help='If provided, attempts to configure a core located in the given directory by removing the managed-schema.xml(renaming), configuring the core to use a classic (non-dynamic) schema, and generating the schema.xml from the template provided in'
        )
        parser.add_argument(
            "-r", "--reload",
            help='If provided, attempts to automatically reload the solr core'
        )


    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        using = options.get('using')
        if not isinstance(connections[using].get_backend(), SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine)." % connections[using].get_backend().connection_alias)

        schema_xml = self.build_template(using=using,tfile=Command.schema_template_loc)
        solrcfg_xml = self.build_template(using=using,tfile=Command.solrcfg_template_loc)

        if options.get('filename'):
            self.stdout.write("Trying to write schema file located at {}".format(options.get('filename')))
            self.write_file(options.get('filename'), schema_xml)
            if options.get('reload'):
                connections[using].get_backend().reload()

        if options.get('configure_dir'):
            cdir = options.get('configure_dir')
            self.stdout.write("Trying to configure core located at {}".format(cdir))
            if os.path.isfile(cdir+'/managed-schema'):
                try:
                    os.rename(cdir+'/managed-schema',cdir+'/managed-schema.old')
                except:
                    raise CommandError('Could not rename managed schema out of the way: {}'.format(cdir+'/managed-schema'))
            try:
                self.write_file(cdir+'/schema.xml', schema_xml)
            except:
                raise CommandError('Could not configure {}: {}'.format(cdir+'/schema.xml',traceback.format_exc()))

            try:
                self.write_file(cdir+'/solrconfig.xml',solrcfg_xml)
            except:
                raise CommandError('Could not configure core to use classic Schema Factory {}'.format(cdir+'/solrconfig.xml'))

        if options.get('reload'):
            core= settings.HAYSTACK_CONNECTIONS['solr']['URL'].rsplit('/',1)[-1]
            if 'ADMIN_URL' not in settings.HAYSTACK_CONNECTIONS['solr']:
                raise ImproperlyConfigured("'ADMIN_URL' must be specifid in the HAYSTACK_CONNECTIONS settins for the backend." )
            if 'URL' not in settings.HAYSTACK_CONNECTIONS['solr']:
                raise ImproperlyConfigured("'URL' to the core must be specifid in the HAYSTACK_CONNECTIONS settins for the backend.")
            try:
                self.stdout.write("Trying to relaod core named {}".format(core))
                resp = requests.get(settings.HAYSTACK_CONNECTIONS['solr']['ADMIN_URL'],params="action=RELOAD&core="+core).text#TODO: Fix when pysolr passes params as request params instead of data
                if resp.find('SolrException')!=-1:
                    raise CommandError('Solr Exception Thrown -- Failed to reload core: {}'.format(resp))
            except CommandError:
                raise
            except:
                raise CommandError('Failed to reload core: {}'.format(traceback.format_exc()))

        if  options.get('filename') is None and options.get('configure_dir') is None and options.get('reload') is None:
            self.print_stdout(schema_xml)

    def build_context(self, using):
        backend = connections[using].get_backend()

        if not isinstance(backend, SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine)." % backend.connection_alias)

        content_field_name, fields = backend.build_schema(
            connections[using].get_unified_index().all_searchfields()
        )
        return {
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': constants.DEFAULT_OPERATOR,
            'ID': constants.ID,
            'DJANGO_CT': constants.DJANGO_CT,
            'DJANGO_ID': constants.DJANGO_ID,
        }

    def build_template(self, using, tfile=schema_template_loc):
        t = loader.get_template(tfile)
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
            os.fsync(schema_file.fileno())
