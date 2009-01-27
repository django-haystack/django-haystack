from django.utils.encoding import smart_unicode
from django.template import loader, Context, TemplateDoesNotExist


class ModelIndex(object):
    """
    Provides the search functionality for a model.
    """
    
    def __init__(self, fields=[], model=None):
        # Avoid a circular import by putting this here
        from djangosearch import backend
        self.fields = fields
        self.model = model
        self.backend = backend.SearchBackend()

    def get_query_set(self):
        """
        Get the default QuerySet to index when doing a full update.
        
        Subclasses can override this method to avoid indexing certain objects.
        """
        return self.model._default_manager.all()

    def flatten(self, obj):
        """
        Flatten an object for indexing.
        
        First, we try to load a template, '{app_name}/{model_name}_index.txt'
        and if found, returns the result of rendering that template. 'object'
        will be in its context.
        
        If the template isn't found, defaults to a newline-joined list of each
        of the object's fields, which may or may not be what you want;
        subclasses which want to influence indexing behavior probably want to
        start here.
        """
        # DRL_FIXME: Should we support the old path as well as Ben S.'s desired path?
        try:
            valid_paths = (
                'search/indexes/%s/%s.txt' % (obj._meta.app_label, obj._meta.module_name),
                '%s/%s_index.txt' % (obj._meta.app_label, obj._meta.module_name),
            )
            t = loader.select_template(valid_paths)
            return t.render(Context({'object': obj}))
        except TemplateDoesNotExist:
            return "\n".join([smart_unicode(getattr(obj, f.attname)) for f in obj._meta.fields])

    def should_index(self, obj):
        """
        Returns True if the given object should be indexed.
        
        Subclasses that limit indexing using get_query_set() should also
        define this method to prevent incremental indexing of excluded
        objects.
        """
        return True

    def get_indexed_fields(self, obj):
        """
        Get the individually indexed fields for this object; returns a list of
        (fieldname, value) tuples.
        
        Indexed fields can be searched individually (i,e, "name:jacob"). Most
        subclasses won't need to override the default behavior, which uses the
        ``fields`` initializer argument.
        
        Duplicate field names are allowed. For instance you could return
        
            [('f', 'value 1'), ('f', 'value 2')]
        
        The engine itself is responsible for collapsing that to the proper
        representation if needed.
        
        """
        fields = []
        for field in self.fields:
            try:
                value = getattr(obj, field)
            except AttributeError:
                continue
            if callable(value):
                value = value()
            elif hasattr(value, 'get_query_set'):
                # default handling for ManyToManyField
                # XXX: note that this is kinda damaged right now because the
                # post_save signal is sent *before* m2m fields are updated.
                # see http://code.djangoproject.com/ticket/5390 for a possible fix.
                value = ','.join([smart_unicode(o) for o in value.get_query_set()])
            db_field = obj._meta.get_field(field)
            fields.append((field, self.backend.prep_value(db_field, value)))
        return fields

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
        """Remove an object from the index. Attached to the class's delete hook."""
        self.backend.remove(instance)

    def clear(self):
        """Clear the entire index"""
        self.backend.clear(models=[self.model])

    def reindex(self):
        """Completely clear the index for this model and rebuild it."""
        self.clear()
        self.update()
