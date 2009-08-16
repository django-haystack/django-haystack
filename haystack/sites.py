from django.db.models.base import ModelBase
from haystack.exceptions import AlreadyRegistered, NotRegistered, SearchFieldError
try:
    set
except NameError:
    from sets import Set as set


class SearchSite(object):
    """
    Encapsulates all the indexes that should be available.
    
    This allows you to register indexes on models you don't control (reusable
    apps, django.contrib, etc.) as well as customize on a per-site basis what
    indexes should be available (different indexes for different sites, same
    codebase).
    
    A SearchSite instance should be instantiated in your URLconf, since all
    models will have been loaded by that point.
    
    The API intentionally follows that of django.contrib.admin's AdminSite as
    much as it makes sense to do.
    """
    
    def __init__(self):
        self._registry = {}
    
    def register(self, model, index_class=None):
        """
        Registers a model with the site.
        
        The model should be a Model class, not instances.
        
        If no custom index is provided, a generic SearchIndex will be applied
        to the model.
        """
        if not index_class:
            from haystack.indexes import BasicSearchIndex
            index_class = BasicSearchIndex
        
        if not isinstance(model, ModelBase):
            raise AttributeError('The model being registered must derive from Model.')
        
        if model in self._registry:
            raise AlreadyRegistered('The model %s is already registered' % model.__class__)
        
        self._registry[model] = index_class(model)
        self._setup(model, self._registry[model])
    
    def unregister(self, model):
        """
        Unregisters a model from the site.
        """
        if model not in self._registry:
            raise NotRegistered('The model %s is not registered' % model.__class__)
        self._teardown(model, self._registry[model])
        del(self._registry[model])
    
    def _setup(self, model, index):
        index._setup_save(model)
        index._setup_delete(model)
    
    def _teardown(self, model, index):
        index._teardown_save(model)
        index._teardown_delete(model)
    
    def get_index(self, model):
        """Provide the index that're being used for a particular model."""
        if model not in self._registry:
            raise NotRegistered('The model %s is not registered' % model.__class__)
        return self._registry[model]
    
    def get_indexes(self):
        """Provide a dict of all indexes that're being used."""
        return self._registry
    
    def get_indexed_models(self):
        """Provide a list of all models being indexed."""
        return self._registry.keys()
    
    def all_searchfields(self):
        """
        Builds a dictionary of all fields appearing in any of the `SearchIndex`
        instances registered with a site.
        
        This is useful when building a schema for an engine. A dictionary is
        returned, with each key being a fieldname and the value being the
        `SearchField` class assigned to it.
        """
        content_field_name = ''
        fields = {}
        field_names = set()
        
        for model, index in self.get_indexes().items():
            for field_name, field_object in index.fields.items():
                if field_name in field_names:
                    # We've already got this field in the list. Skip.
                    continue
                
                field_names.add(field_name)
                
                if field_object.document is True:
                    if content_field_name != '' and content_field_name != field_name:
                        raise SearchFieldError("All SearchIndex fields with 'document=True' must use the same fieldname.")
                    
                    content_field_name = field_name
                
                fields[field_name] = field_object
        
        return fields
    
    def update_object(self, instance):
        """
        Updates the instance's data in the index.
        
        A shortcut for updating on the instance's index. Errors from `get_index`
        and `update_object` will be allowed to propogate.
        """
        return self.get_index(type(instance)).update_object(instance)
    
    def remove_object(self, instance):
        """
        Removes the instance's data in the index.
        
        A shortcut for removing on the instance's index. Errors from `get_index`
        and `remove_object` will be allowed to propogate.
        """
        return self.get_index(type(instance)).remove_object(instance)


# The common case. Feel free to override/replace/define your own in your URLconfs.
site = SearchSite()
