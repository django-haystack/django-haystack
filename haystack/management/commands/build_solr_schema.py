import os

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.template import loader

from haystack import connections, constants
from haystack.backends.solr_backend import SolrSearchBackend


class Command(BaseCommand):
    help = (  # noqa A003
        "Generates a Solr schema that reflects the indexes using templates "
        " under a django template dir 'search_configuration/*.xml'.  If none are "
        " found, then provides defaults suitable to Solr 6.4"
    )
    schema_template_loc = "search_configuration/schema.xml"
    solrcfg_template_loc = "search_configuration/solrconfig.xml"

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--filename",
            help="Generate schema.xml directly into a file instead of stdout."
            " Does not render solrconfig.xml",
        )
        parser.add_argument(
            "-u",
            "--using",
            default=constants.DEFAULT_ALIAS,
            help="Select a specific Solr connection to work with.",
        )
        parser.add_argument(
            "-c",
            "--configure-directory",
            help="Attempt to configure a core located in the given directory"
            " by removing the managed-schema.xml(renaming) if it "
            " exists, configuring the core by rendering the schema.xml and "
            " solrconfig.xml templates provided in the django project's "
            " TEMPLATE_DIR/search_configuration directories",
        )
        parser.add_argument(
            "-r",
            "--reload-core",
            help="If provided, attempts to automatically reload the solr core"
            ' via the urls in the "URL" and "ADMIN_URL" settings of the SOLR'
            " HAYSTACK_CONNECTIONS entry. Both MUST be set.",
        )

    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        using = options.get("using")
        if not isinstance(connections[using].get_backend(), SolrSearchBackend):
            raise ImproperlyConfigured("'%s' isn't configured as a SolrEngine" % using)

        schema_xml = self.build_template(
            using=using, template_filename=Command.schema_template_loc
        )
        solrcfg_xml = self.build_template(
            using=using, template_filename=Command.solrcfg_template_loc
        )

        filename = options.get("filename")
        configure_directory = options.get("configure_directory")
        reload_core = options.get("reload_core")

        if filename:
            self.stdout.write(
                "Trying to write schema file located at {}".format(filename)
            )
            self.write_file(filename, schema_xml)

            if reload_core:
                connections[using].get_backend().reload()

        if configure_directory:
            self.stdout.write(
                "Trying to configure core located at {}".format(configure_directory)
            )

            managed_schema_path = os.path.join(configure_directory, "managed-schema")

            if os.path.isfile(managed_schema_path):
                try:
                    os.rename(managed_schema_path, "%s.old" % managed_schema_path)
                except OSError as exc:
                    raise CommandError(
                        "Could not rename old managed schema file {}: {}".format(
                            managed_schema_path, exc
                        )
                    )

            schema_xml_path = os.path.join(configure_directory, "schema.xml")

            try:
                self.write_file(schema_xml_path, schema_xml)
            except EnvironmentError as exc:
                raise CommandError(
                    "Could not configure {}: {}".format(schema_xml_path, exc)
                )

            solrconfig_path = os.path.join(configure_directory, "solrconfig.xml")

            try:
                self.write_file(solrconfig_path, solrcfg_xml)
            except EnvironmentError as exc:
                raise CommandError(
                    "Could not write {}: {}".format(solrconfig_path, exc)
                )

        if reload_core:
            core = settings.HAYSTACK_CONNECTIONS[using]["URL"].rsplit("/", 1)[-1]

            if "ADMIN_URL" not in settings.HAYSTACK_CONNECTIONS[using]:
                raise ImproperlyConfigured(
                    "'ADMIN_URL' must be specified in the HAYSTACK_CONNECTIONS"
                    " for the %s backend" % using
                )
            if "URL" not in settings.HAYSTACK_CONNECTIONS[using]:
                raise ImproperlyConfigured(
                    "'URL' must be specified in the HAYSTACK_CONNECTIONS"
                    " for the %s backend" % using
                )

            try:
                self.stdout.write("Trying to reload core named {}".format(core))
                resp = requests.get(
                    settings.HAYSTACK_CONNECTIONS[using]["ADMIN_URL"],
                    params={"action": "RELOAD", "core": core},
                )

                if not resp.ok:
                    raise CommandError(
                        "Failed to reload core – Solr error: {}".format(resp)
                    )
            except CommandError:
                raise
            except Exception as exc:
                raise CommandError("Failed to reload core {}: {}".format(core, exc))

        if not filename and not configure_directory and not reload_core:
            self.print_stdout(schema_xml)

    def build_context(self, using):
        backend = connections[using].get_backend()

        if not isinstance(backend, SolrSearchBackend):
            raise ImproperlyConfigured(
                "'%s' isn't configured as a SolrEngine" % backend.connection_alias
            )

        content_field_name, fields = backend.build_schema(
            connections[using].get_unified_index().all_searchfields()
        )
        return {
            "content_field_name": content_field_name,
            "fields": fields,
            "default_operator": constants.DEFAULT_OPERATOR,
            "ID": constants.ID,
            "DJANGO_CT": constants.DJANGO_CT,
            "DJANGO_ID": constants.DJANGO_ID,
        }

    def build_template(self, using, template_filename=schema_template_loc):
        t = loader.get_template(template_filename)
        c = self.build_context(using=using)
        return t.render(c)

    def print_stdout(self, schema_xml):
        self.stderr.write("\n")
        self.stderr.write("\n")
        self.stderr.write("\n")
        self.stderr.write(
            "Save the following output to 'schema.xml' and place it in your Solr configuration directory.\n"
        )
        self.stderr.write(
            "--------------------------------------------------------------------------------------------\n"
        )
        self.stderr.write("\n")
        self.stdout.write(schema_xml)

    def write_file(self, filename, schema_xml):
        with open(filename, "w") as schema_file:
            schema_file.write(schema_xml)
            os.fsync(schema_file.fileno())
