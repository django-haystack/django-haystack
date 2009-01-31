from django.template import loader, Context
import djangosearch


class SearchFieldError(Exception):
    pass


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = [(field_name, attrs.pop(field_name)) for field_name, obj in attrs.items() if isinstance(obj, SearchField)]
        return super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)


class ModelIndex(object):
    """
    Base class for building indexes.
    
    An example might look like this::
    
        import datetime
        from djangosearch import indexes
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
        self.backend = backend or djangosearch.backend()
        content_fields = []
        
        for field_name, field in self.fields:
            if isinstance(field, ContentField):
                content_fields.append(field)
        
        if len(content_fields) <= 0 or len(content_fields) > 1:
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
        return [(field_name, self.backend.prep_value(field.get_value(obj))) for field_name, field in self.fields]

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


# All the SearchFields variants.

class SearchField(object):
    def __init__(self, db_field_name):
        self.db_field_name = db_field_name
    
    def get_value(self, obj):
        return getattr(obj, self.db_field_name, '')


class ContentField(SearchField):
    def __init__(self):
        self.db_field_name = None
    
    def get_value(self, obj):
        """
        Flatten an object for indexing.
        
        This loads a template, ``search/indexes/{app_label}/{model_name}.txt``
        and returns the result of rendering that template. ``object``
        will be in its context.
        """
        t = loader.get_template('search/indexes/%s/%s.txt' % (obj._meta.app_label, obj._meta.module_name))
        return t.render(Context({'object': obj}))


class CharField(SearchField):
    pass


class NumberField(SearchField):
    pass


class DateField(SearchField):
    pass


class TimeField(SearchField):
    pass


class DateTimeField(SearchField):
    pass


class MultiValueField(SearchField):
    pass


class StoredField(SearchField):
    def get_value(self, obj):
        """
        Flatten an object for storage (non-indexed).
        
        This is useful if you know in advance what you want to display in the
        search results and want to save on hits to the DB.
        """
        t = loader.get_template('search/indexes/%s/%s_stored.txt' % (obj._meta.app_label, obj._meta.module_name))
        return t.render(Context({'object': obj}))
