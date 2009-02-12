from django.core.management.base import NoArgsCommand
from django.template import loader, Context
from haystack.constants import DEFAULT_OPERATOR
from haystack.fields import *
try:
    set
except NameError:
    from sets import Set as set


class Command(NoArgsCommand):
    help = "Generates a Solr schema that reflects the indexes."
    
    def handle_noargs(self, **options):
        """Generates a Solr schema that reflects the indexes."""
        # Cause the default site to load.
        from django.conf import settings
        __import__(settings.ROOT_URLCONF)
        from haystack.sites import site
        
        content_field_name = ''
        fields = []
        field_names = set()
        default_operator = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', DEFAULT_OPERATOR)
        
        for model, index in site.get_indexes().items():
            for field_name, field_object in index.fields.items():
                if field_name in field_names:
                    # We've already got this field in the list. Skip.
                    continue
                
                field_names.add(field_name)
                
                field_data = {
                    'field_name': field_name,
                    'type': 'text',
                    'indexed': 'true',
                    'multi_valued': 'false',
                }
                
                # Nasty but...
                if isinstance(field_object, ContentField):
                    content_field_name = field_name
                elif isinstance(field_object, StoredField):
                    field_data['indexed'] = 'false'
                elif isinstance(field_object, DateField) or isinstance(field_object, DateTimeField):
                    field_data['type'] = 'date'
                elif isinstance(field_object, IntegerField):
                    field_data['type'] = 'slong'
                elif isinstance(field_object, FloatField):
                    field_data['type'] = 'sfloat'
                elif isinstance(field_object, BooleanField):
                    field_data['type'] = 'boolean'
                elif isinstance(field_object, MultiValueField):
                    field_data['multi_valued'] = 'true'
            
                fields.append(field_data)
        
        t = loader.get_template('search_configuration/solr.xml')
        c = Context({
            'content_field_name': content_field_name,
            'fields': fields,
            'default_operator': default_operator,
        })
        schema_xml = t.render(c)
        print
        print
        print
        print "Save the following output to 'schema.xml' and place it in your Solr configuration directory."
        print '--------------------------------------------------------------------------------------------'
        print
        print schema_xml
