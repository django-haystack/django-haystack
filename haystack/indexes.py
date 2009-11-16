from django.db.models import signals
from django.utils.encoding import force_unicode
import haystack
from haystack.fields import *
from haystack.utils import get_identifier


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
                field.instance_name = field_name
                attrs['fields'][field_name] = field
        
        return super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)


# DRL_FIXME: Before 1.0, this should become ``SearchIndex`` again.
class BaseSearchIndex(object):
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
            
            def get_queryset(self):
                return super(NoteIndex, self).get_queryset().filter(pub_date__lte=datetime.datetime.now())
    
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
            self.prepared_data[field_name] = field.prepare(obj)
        
        for field_name, field in self.fields.items():
            if hasattr(self, "prepare_%s" % field_name):
                value = getattr(self, "prepare_%s" % field_name)(obj)
                self.prepared_data[field_name] = value
        
        # Remove any fields that lack a value and are `null=True`.
        for field_name, field in self.fields.items():
            if field.null is True:
                if self.prepared_data[field_name] is None:
                    del(self.prepared_data[field_name])
        
        return self.prepared_data
    
    def get_content_field(self):
        """Returns the field that supplies the primary document to be indexed."""
        for field_name, field in self.fields.items():
            if field.document is True:
                return field_name
    
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


# DRL_FIXME: Before 1.0, this should become ``RealTimeSearchIndex``.
class SearchIndex(BaseSearchIndex):
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


def fields_for_searchindex(model, existing_fields, fields=None, excludes=None):
    """
    Used by the `ModelSearchIndex` class to generate a field list by
    introspecting the model.
    """
    final_fields = {}
    
    if fields is None:
        fields = []
    
    if excludes is None:
        excludes = []
    
    for f in model._meta.fields:
        if f.name in existing_fields:
            continue
        
        if fields and f.name not in fields:
            continue
        
        if excludes and f.name in excludes:
            continue
        
        # Skip reserved fieldnames from Haystack.
        if f.name in ('id', 'django_ct', 'django_id', 'content', 'text'):
            continue
        
        # Ignore certain fields (AutoField, related fields).
        if f.primary_key or getattr(f, 'rel'):
            continue
        
        if f.get_internal_type() in ('DateField', 'DateTimeField'):
            index_field_class = DateTimeField
        elif f.get_internal_type() in ('BooleanField', 'NullBooleanField'):
            index_field_class = BooleanField
        elif f.get_internal_type() in ('CommaSeparatedIntegerField',):
            index_field_class = MultiValueField
        elif f.get_internal_type() in ('DecimalField', 'FloatField'):
            index_field_class = FloatField
        elif f.get_internal_type() in ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField'):
            index_field_class = FloatField
        else:
            index_field_class = CharField
        
        kwargs = {
            'model_attr': f.name,
        }
        
        if f.null is True:
            kwargs['null'] = True
        
        if f.has_default():
            kwargs['default'] = f.default
        
        final_fields[f.name] = index_field_class(**kwargs)
    
    return final_fields


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
    
    def __init__(self, model, backend=None):
        self.model = model
        self.backend = backend or haystack.backend.SearchBackend()
        self.prepared_data = None
        content_fields = []
        
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        self._meta = getattr(self, 'Meta', None)
        
        if self._meta:
            fields = []
            excludes = []
            
            if getattr(self._meta, 'fields', None):
                fields = self._meta.fields
            
            if getattr(self._meta, 'excludes', None):
                excludes = self._meta.excludes
            
            # Add in the new fields.
            self.fields.update(fields_for_searchindex(self.model, self.fields, fields, excludes))
        
        for field_name, field in self.fields.items():
            if field.document is True:
                content_fields.append(field_name)
        
        if not len(content_fields) == 1:
            raise SearchFieldError("An index must have one (and only one) SearchField with document=True.")
