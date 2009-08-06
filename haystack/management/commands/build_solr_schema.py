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
        from haystack import site
        
        default_operator = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', DEFAULT_OPERATOR)
        content_field_name, fields = site.build_unified_schema()
        translated_fields = []
        
        for field in fields:
            if field['type'] == 'long':
                field['type'] = 'slong'
            
            if field['type'] == 'float':
                field['type'] = 'sfloat'
            
            if field['type'] == 'datetime':
                field['type'] = 'date'
            
            translated_fields.append(field)
        
        t = loader.get_template('search_configuration/solr.xml')
        c = Context({
            'content_field_name': content_field_name,
            'fields': translated_fields,
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
