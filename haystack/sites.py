import copy
from haystack.exceptions import AlreadyRegistered, NotRegistered, SearchFieldError


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
        self._cached_field_mapping = None
    
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
        
        if not hasattr(model, '_meta'):
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
        returned, with each key being a fieldname (or index_fieldname) and the
        value being the `SearchField` class assigned to it.
        """
        content_field_name = ''
        fields = {}
        
        for model, index in self.get_indexes().items():
            for field_name, field_object in index.fields.items():
                if field_object.document is True:
                    if content_field_name != '' and content_field_name != field_object.index_fieldname:
                        raise SearchFieldError("All SearchIndex fields with 'document=True' must use the same fieldname.")
                    
                    content_field_name = field_object.index_fieldname
                
                if not field_object.index_fieldname in fields:
                    fields[field_object.index_fieldname] = field_object
                    fields[field_object.index_fieldname] = copy.copy(field_object)
                else:
                    # If the field types are different, we can mostly
                    # safely ignore this. The exception is ``MultiValueField``,
                    # in which case we'll use it instead, copying over the
                    # values.
                    if field_object.is_multivalued == True:
                        old_field = fields[field_object.index_fieldname]
                        fields[field_object.index_fieldname] = field_object
                        fields[field_object.index_fieldname] = copy.copy(field_object)
                        
                        # Switch it so we don't have to dupe the remaining
                        # checks.
                        field_object = old_field
                    
                    # We've already got this field in the list. Ensure that
                    # what we hand back is a superset of all options that
                    # affect the schema.
                    if field_object.indexed is True:
                        fields[field_object.index_fieldname].indexed = True
                    
                    if field_object.stored is True:
                        fields[field_object.index_fieldname].stored = True
                    
                    if field_object.faceted is True:
                        fields[field_object.index_fieldname].faceted = True
                    
                    if field_object.use_template is True:
                        fields[field_object.index_fieldname].use_template = True
                    
                    if field_object.null is True:
                        fields[field_object.index_fieldname].null = True
        
        return fields
    
    def get_index_fieldname(self, fieldname):
        """
        Returns the actual name of the field in the index.
        
        If not found, returns the fieldname provided.
        
        This is useful because it handles the case where a ``index_fieldname``
        was provided, allowing the user to use the variable name from their
        ``SearchIndex`` instead of having to remember & use the overridden
        name.
        """
        if fieldname in self._field_mapping():
            return self._field_mapping()[fieldname]['index_fieldname']
        else:
            return fieldname
    
    def get_facet_field_name(self, fieldname):
        """
        Returns the actual name of the facet field in the index.
        
        If not found, returns the fieldname provided.
        """
        facet_fieldname = None
        
        reverse_map = {}
        
        for field, info in self._field_mapping().items():
            if info['facet_fieldname'] and info['facet_fieldname'] == fieldname:
                return info['index_fieldname']
        
        return self.get_index_fieldname(fieldname)
    
    def _field_mapping(self):
        mapping = {}
        
        if self._cached_field_mapping:
            return self._cached_field_mapping
        
        for model, index in self.get_indexes().items():
            for field_name, field_object in index.fields.items():
                if field_name in mapping and field_object.index_fieldname != mapping[field_name]['index_fieldname']:
                    # We've already seen this field in the list. Raise an exception if index_fieldname differs.
                    raise SearchFieldError("All uses of the '%s' field need to use the same 'index_fieldname' attribute." % field_name)
                
                facet_fieldname = None
                
                if hasattr(field_object, 'facet_for'):
                    if field_object.facet_for:
                        facet_fieldname = field_object.facet_for
                    else:
                        facet_fieldname = field_object.instance_name
                
                mapping[field_name] = {
                    'index_fieldname': field_object.index_fieldname,
                    'facet_fieldname': facet_fieldname,
                }
        
        self._cached_field_mapping = mapping
        return mapping
    
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
