import haystack
from haystack.fields import *


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}
        
        for field_name, obj in attrs.items():
            if isinstance(obj, SearchField):
                field = attrs.pop(field_name)
                field.instance_name = field_name
                attrs['fields'][field_name] = field
        
        return super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)


class SearchIndex(object):
    """
    Base class for building indexes.
    
    An example might look like this::
    
        import datetime
        from haystack import indexes
        from myapp.models import Note
        
        class NoteIndex(indexes.SearchIndex):
            text = indexes.CharField(document=True, use_template=True)
            author = indexes.CharField(model_attr='user')
            pub_date = indexes.DateTimeField(model_attr='pub_date')
            
            def get_query_set(self):
                return super(NoteIndex, self).get_query_set().filter(pub_date__lte=datetime.datetime.now())
    
    """
    __metaclass__ = DeclarativeMetaclass
    
    def __init__(self, model, backend=None):
        self.model = model
        self.backend = backend or haystack.backend.SearchBackend()
        self.prepared_data = None
        content_fields = []
        
        for field_name, field in self.fields.items():
            if field.document is True:
                content_fields.append(field_name)
        
        if not len(content_fields) == 1:
            raise SearchFieldError("An index must have one (and only one) SearchField with document=True.")
    
    def get_query_set(self):
        """
        Get the default QuerySet to index when doing a full update.
        
        Subclasses can override this method to avoid indexing certain objects.
        """
        return self.model._default_manager.all()
    
    def prepare(self, obj):
        """
        Fetches and adds/alters data before indexing.
        """
        self.prepared_data = {}
        
        for field_name, field in self.fields.items():
            self.prepared_data[field_name] = field.prepare(obj)
        
        for field_name, field in self.fields.items():
            if hasattr(self, "prepare_%s" % field_name):
                value = getattr(self, "prepare_%s" % field_name)(obj)
                self.prepared_data[field_name] = value
        
        return self.prepared_data
    
    def get_content_field(self):
        """Returns the field that supplies the primary document to be indexed."""
        for field_name, field in self.fields.items():
            if field.document is True:
                return field_name

    def update(self):
        """Update the entire index"""
        self.backend.update(self, self.get_query_set())

    def update_object(self, instance, **kwargs):
        """
        Update the index for a single object. Attached to the class's
        post-save hook.
        """
        self.backend.update(self, [instance])

    def remove_object(self, instance, **kwargs):
        """
        Remove an object from the index. Attached to the class's 
        post-delete hook.
        """
        self.backend.remove(instance)

    def clear(self):
        """Clear the entire index."""
        self.backend.clear(models=[self.model])

    def reindex(self):
        """Completely clear the index for this model and rebuild it."""
        self.clear()
        self.update()


class BasicSearchIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
