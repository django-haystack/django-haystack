from optparse import make_option
import sys
from django.core.management.base import BaseCommand
from django.template import loader, Context
from haystack.constants import ID, DJANGO_CT, DJANGO_ID, DEFAULT_OPERATOR, DEFAULT_ALIAS


class Command(BaseCommand):
    help = "Generates a Solr schema that reflects the indexes."
    base_options = (
        make_option("-f", "--filename", action="store", type="string",
                    dest="filename",
                    help="""If provided, directs output to a file instead of
                    stdout."""),
        make_option("-u", "--using", action="store", type="string",
                    dest="using", default=DEFAULT_ALIAS,
                    help='If provided, chooses a connection to work with.'),
        make_option("-t", "--template", action="store", type="string",
                    dest="template",
                    help="""If provided, generates schema.xml from custom
                    template instead of Haystack's default.""",
                    default="search_configuration/solr.xml"),
    )
    option_list = BaseCommand.option_list + base_options

    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        using = options.get('using')
        template = options.get('template')
        schema_xml = self.build_template(using=using, template=template)

        if options.get('filename'):
            self.write_file(options.get('filename'), schema_xml)
        else:
            self.print_stdout(schema_xml)

    def build_context(self, using):
        from haystack import connections, connection_router
        backend = connections[using].get_backend()
        content_field_name, fields = backend.build_schema(connections[using].get_unified_index().all_searchfields())
        return Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': DEFAULT_OPERATOR,
            'ID': ID,
            'DJANGO_CT': DJANGO_CT,
            'DJANGO_ID': DJANGO_ID,
        })

    def build_template(self, using, template):
        t = loader.get_template(template)
        c = self.build_context(using=using)
        return t.render(c)

    def print_stdout(self, schema_xml):
        sys.stderr.write("\n")
        sys.stderr.write("\n")
        sys.stderr.write("\n")
        sys.stderr.write("Save the following output to 'schema.xml' and place it in your Solr configuration directory.\n")
        sys.stderr.write("--------------------------------------------------------------------------------------------\n")
        sys.stderr.write("\n")
        print schema_xml

    def write_file(self, filename, schema_xml):
        schema_file = open(filename, 'w')
        schema_file.write(schema_xml)
        schema_file.close()
