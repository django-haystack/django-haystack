import sys
from django.core.management.base import NoArgsCommand
from django.template import loader, Context
from haystack.constants import DEFAULT_OPERATOR


class Command(NoArgsCommand):
    help = "Generates a Solr schema that reflects the indexes."
    
    def handle_noargs(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        # Cause the default site to load.
        from django.conf import settings
        from haystack import backend, site
        
        default_operator = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', DEFAULT_OPERATOR)
        content_field_name, fields = backend.SearchBackend().build_schema(site.all_searchfields())
        
        t = loader.get_template('search_configuration/solr.xml')
        c = Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': default_operator,
        })
        schema_xml = t.render(c)
        sys.stderr.write("\n")
        sys.stderr.write("\n")
        sys.stderr.write("\n")
        sys.stderr.write("Save the following output to 'schema.xml' and place it in your Solr configuration directory.\n")
        sys.stderr.write("--------------------------------------------------------------------------------------------\n")
        sys.stderr.write("\n")
        print schema_xml
