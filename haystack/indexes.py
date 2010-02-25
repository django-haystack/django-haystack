import copy
from django.db.models import signals
from django.utils.encoding import force_unicode
from haystack.fields import *
from haystack.utils import get_identifier, get_facet_field_name


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}
        
        # Inherit any fields from parent(s).
        try:
            parents = [b for b in bases if issubclass(b, SearchIndex)]
            
            for p in parents:
                fields = getattr(p, 'fields', None)
                
                if fields:
                    attrs['fields'].update(fields)
        except NameError:
            pass
        
        for field_name, obj in attrs.items():
            if isinstance(obj, SearchField):
                field = attrs.pop(field_name)
                field.set_instance_name(field_name)
                attrs['fields'][field_name] = field
        
        return super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)


class SearchIndex(object):
    """
    Base class for building indexes.
    
    An example might look like this::
    
        import datetime
        from haystack.indexes import *
        from myapp.models import Note
        
        class NoteIndex(SearchIndex):
            text = CharField(document=True, use_template=True)
            author = CharField(model_attr='user')
            pub_date = DateTimeField(model_attr='pub_date')
            
            def get_queryset(self):
                return super(NoteIndex, self).get_queryset().filter(pub_date__lte=datetime.datetime.now())
    
    """
    __metaclass__ = DeclarativeMetaclass
    
    def __init__(self, model, backend=None):
        self.model = model
        
        if backend:
            self.backend = backend
        else:
            import haystack
            self.backend = haystack.backend.SearchBackend()
        
        self.prepared_data = None
        content_fields = []
        
        for field_name, field in self.fields.items():
            if field.document is True:
                content_fields.append(field_name)
        
        if not len(content_fields) == 1:
            raise SearchFieldError("An index must have one (and only one) SearchField with document=True.")
    
    def _setup_save(self, model):
        """A hook for controlling what happens when the registered model is saved."""
        pass
    
    def _setup_delete(self, model):
        """A hook for controlling what happens when the registered model is deleted."""
        pass
    
    def _teardown_save(self, model):
        """A hook for removing the behavior when the registered model is saved."""
        pass
    
    def _teardown_delete(self, model):
        """A hook for removing the behavior when the registered model is deleted."""
        pass
    
    def get_queryset(self):
        """
        Get the default QuerySet to index when doing a full update.
        
        Subclasses can override this method to avoid indexing certain objects.
        """
        return self.model._default_manager.all()
    
    def prepare(self, obj):
        """
        Fetches and adds/alters data before indexing.
        """
        self.prepared_data = {
            'id': get_identifier(obj),
            'django_ct': "%s.%s" % (obj._meta.app_label, obj._meta.module_name),
            'django_id': force_unicode(obj.pk),
        }
        
        for field_name, field in self.fields.items():
            # Use the possibly overridden name, which will default to the
            # variable name of the field.
            self.prepared_data[field.index_fieldname] = field.prepare(obj)
        
        for field_name, field in self.fields.items():
            if hasattr(self, "prepare_%s" % field_name):
                value = getattr(self, "prepare_%s" % field_name)(obj)
                self.prepared_data[field.index_fieldname] = value
        
        # Remove any fields that lack a value and are `null=True`.
        for field_name, field in self.fields.items():
            if field.null is True:
                if self.prepared_data[field.index_fieldname] is None:
                    del(self.prepared_data[field.index_fieldname])
        
        return self.prepared_data
    
    def full_prepare(self, obj):
        self.prepared_data = self.prepare(obj)
        
        # Duplicate data for faceted fields.
        for field_name, field in self.fields.items():
            if field.faceted is True:
                self.prepared_data[get_facet_field_name(field.index_fieldname)] = self.prepared_data[field.index_fieldname]
        
        return self.prepared_data
    
    def get_content_field(self):
        """Returns the field that supplies the primary document to be indexed."""
        for field_name, field in self.fields.items():
            if field.document is True:
                return field.index_fieldname
    
    def update(self):
        """Update the entire index"""
        self.backend.update(self, self.get_queryset())
    
    def update_object(self, instance, **kwargs):
        """
        Update the index for a single object. Attached to the class's
        post-save hook.
        """
        # Check to make sure we want to index this first.
        if self.should_update(instance, **kwargs):
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
    
    def get_updated_field(self):
        """
        Get the field name that represents the updated date for the model.
        
        If specified, this is used by the reindex command to filter out results
        from the QuerySet, enabling you to reindex only recent records. This
        method should either return None (reindex everything always) or a
        string of the Model's DateField/DateTimeField name.
        """
        return None
    
    def should_update(self, instance, **kwargs):
        """
        Determine if an object should be updated in the index.
        
        It's useful to override this when an object may save frequently and
        cause excessive reindexing. You should check conditions on the instance
        and return False if it is not to be indexed.
        
        By default, returns True (always reindex).
        """
        return True
    
    def load_all_queryset(self):
        """
        Provides the ability to override how objects get loaded in conjunction
        with ``SearchQuerySet.load_all``.
        
        This is useful for post-processing the results from the query, enabling
        things like adding ``select_related`` or filtering certain data.
        
        By default, returns ``all()`` on the model's default manager.
        """
        return self.model._default_manager.all()


class RealTimeSearchIndex(SearchIndex):
    """
    A variant of the ``SearchIndex`` that constantly keeps the index fresh,
    as opposed to requiring a cron job.
    """
    def _setup_save(self, model):
        signals.post_save.connect(self.update_object, sender=model)
    
    def _setup_delete(self, model):
        signals.post_delete.connect(self.remove_object, sender=model)
    
    def _teardown_save(self, model):
        signals.post_save.disconnect(self.update_object, sender=model)
    
    def _teardown_delete(self, model):
        signals.post_delete.disconnect(self.remove_object, sender=model)


class BasicSearchIndex(SearchIndex):
    text = CharField(document=True, use_template=True)


# End SearchIndexes
# Begin ModelSearchIndexes


def index_field_from_django_field(f, default=CharField):
    """
    Returns the Haystack field type that would likely be associated with each
    Django type.
    """
    result = default
    
    if f.get_internal_type() in ('DateField', 'DateTimeField'):
        result = DateTimeField
    elif f.get_internal_type() in ('BooleanField', 'NullBooleanField'):
        result = BooleanField
    elif f.get_internal_type() in ('CommaSeparatedIntegerField',):
        result = MultiValueField
    elif f.get_internal_type() in ('DecimalField', 'FloatField'):
        result = FloatField
    elif f.get_internal_type() in ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField'):
        result = FloatField
    
    return result


class ModelSearchIndex(SearchIndex):
    """
    Introspects the model assigned to it and generates a `SearchIndex` based on
    the fields of that model.
    
    In addition, it adds a `text` field that is the `document=True` field and
    has `use_template=True` option set, just like the `BasicSearchIndex`.
    
    Usage of this class might result in inferior `SearchIndex` objects, which
    can directly affect your search results. Use this to establish basic
    functionality and move to custom `SearchIndex` objects for better control.
    
    At this time, it does not handle related fields.
    """
    text = CharField(document=True, use_template=True)
    # list of reserved field names
    fields_to_skip = ('id', 'django_ct', 'django_id', 'content', 'text')
    
    def __init__(self, model, backend=None, extra_field_kwargs=None):
        self.model = model
        
        if backend:
            self.backend = backend
        else:
            import haystack
            self.backend = haystack.backend.SearchBackend()
        
        self.prepared_data = None
        content_fields = []
        self.extra_field_kwargs = extra_field_kwargs or {}
        
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        self._meta = getattr(self, 'Meta', None)
        
        if self._meta:
            fields = getattr(self._meta, 'fields', [])
            excludes = getattr(self._meta, 'excludes', [])
            
            # Add in the new fields.
            self.fields.update(self.get_fields(fields, excludes))
        
        for field_name, field in self.fields.items():
            if field.document is True:
                content_fields.append(field_name)
        
        if not len(content_fields) == 1:
            raise SearchFieldError("An index must have one (and only one) SearchField with document=True.")
    
    def should_skip_field(self, field):
        """
        Given a Django model field, return if it should be included in the
        contributed SearchFields.
        """
        # Skip fields in skip list
        if field.name in self.fields_to_skip:
            return True
        
        # Ignore certain fields (AutoField, related fields).
        if field.primary_key or getattr(field, 'rel'):
            return True
        
        return False
    
    def get_index_fieldname(self, f):
        """
        Given a Django field, return the appropriate index fieldname.
        """
        return f.name
    
    def get_fields(self, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []
        
        for f in self.model._meta.fields:
            # If the field name is already present, skip
            if f.name in self.fields:
                continue
            
            # If field is not present in explicit field listing, skip
            if fields and f.name not in fields:
                continue
            
            # If field is in exclude list, skip
            if excludes and f.name in excludes:
                continue
            
            if self.should_skip_field(f):
                continue
            
            index_field_class = index_field_from_django_field(f)
            
            kwargs = copy.copy(self.extra_field_kwargs)
            kwargs.update({
                'model_attr': f.name,
            })
            
            if f.null is True:
                kwargs['null'] = True
            
            if f.has_default():
                kwargs['default'] = f.default
            
            final_fields[f.name] = index_field_class(**kwargs)
            final_fields[f.name].set_instance_name(self.get_index_fieldname(f))
        
        return final_fields
