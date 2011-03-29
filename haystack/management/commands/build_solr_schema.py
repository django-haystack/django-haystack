from optparse import make_option
import sys
from django.core.management.base import BaseCommand
from django.template import loader, Context
from haystack.constants import ID, DJANGO_CT, DJANGO_ID, DEFAULT_OPERATOR
try:
    from django.utils import importlib
except ImportError:
    from haystack.utils import importlib

class Command(BaseCommand):
    help = "Generates a Solr schema that reflects the indexes."
    base_options = (
        make_option("-f", "--filename", action="store", type="string", dest="filename",
                    help='If provided, directs output to a file instead of stdout.'),
        make_option("-s", "--site", action="store", type="string", dest="site",
                    help='If provided, configures Haystack to use the appropriate site module. (Defaults to `haystack.site`)'),
    )
    option_list = BaseCommand.option_list + base_options
    
    def handle(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        if options.get('site'):
            mod_name, attr_name = options['site'].rsplit('.', 1)
            self.site = getattr(importlib.import_module(mod_name), attr_name)
        else:
            from haystack import site
            self.site = site

        schema_xml = self.build_template()
        
        if options.get('filename'):
            self.write_file(options.get('filename'), schema_xml)
        else:
            self.print_stdout(schema_xml)
    
    def build_context(self):
        # Cause the default site to load.
        content_field_name, fields = self.site.backend.build_schema(self.site.all_searchfields())
        return Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': DEFAULT_OPERATOR,
            'ID': ID,
            'DJANGO_CT': DJANGO_CT,
            'DJANGO_ID': DJANGO_ID,
        })
    
    def build_template(self):
        t = loader.get_template('search_configuration/solr.xml')
        c = self.build_context()
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
