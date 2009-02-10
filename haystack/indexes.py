import haystack
from haystack.fields import *


class SearchFieldError(Exception):
    pass


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}
        
        for field_name, obj in attrs.items():
            if isinstance(obj, SearchField):
                field = attrs.pop(field_name)
                field.instance_name = field_name
                attrs['fields'][field_name] = field
        
        return super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)


class ModelIndex(object):
    """
    Base class for building indexes.
    
    An example might look like this::
    
        import datetime
        from haystack import indexes
        from myapp.models import Note
        
        class NoteIndex(indexes.ModelIndex):
            text = indexes.ContentField()
            author = indexes.CharField('user')
            pub_date = indexes.DateTimeField('pub_date')
            
            def get_query_set(self):
                return super(NoteIndex, self).get_query_set().filter(pub_date__lte=datetime.datetime.now())
    
    """
    __metaclass__ = DeclarativeMetaclass
    
    def __init__(self, model, backend=None):
        self.model = model
        self.backend = backend or haystack.backend.SearchBackend()
        content_fields = []
        
        for field_name, field in self.fields.items():
            if isinstance(field, ContentField):
                content_fields.append(field)
        
        if not len(content_fields) == 1:
            raise SearchFieldError("An index must have one ContentField.")

    def get_query_set(self):
        """
        Get the default QuerySet to index when doing a full update.
        
        Subclasses can override this method to avoid indexing certain objects.
        """
        return self.model._default_manager.all()
    
    def get_fields(self, obj):
        """
        Gets the indexed fields for this object and returns a list of tuples.
        
        The tuple format looks like (fieldname, value).
        """
        return [(field_name, field.get_value(obj)) for field_name, field in self.fields.items()]
    
    def get_content_field(self):
        """Returns the """
        for field_name, field in self.fields.items():
            if isinstance(field, ContentField):
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
        """Clear the entire index"""
        self.backend.clear(models=[self.model])

    def reindex(self):
        """Completely clear the index for this model and rebuild it."""
        self.clear()
        self.update()


class BasicModelIndex(ModelIndex):
    text = ContentField()
