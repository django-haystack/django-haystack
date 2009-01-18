from django.db.models import signals
from django.db.models.base import ModelBase
from djangosearch.indexes import ModelIndex


class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass


class IndexSite(object):
    """
    Encapsulates all the indexes that should be available.
    
    This allows you to register indexes on models you don't control (reusable
    apps, django.contrib, etc.) as well as customize on a per-site basis what
    indexes should be available (different indexes for different sites, same
    codebase).
    
    An IndexSite instance should be instantiated in your URLconf, since all
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
        
        If no custom index is provided, a generic ModelIndex will be applied
        to the model.
        """
        if not index_class:
            index_class = ModelIndex
        
        # FIXME: Too draconian? Is a class that quacks like a Model good enough?
        if not isinstance(model, ModelBase):
            raise AttributeError('The model being registered must derive from Model.')
        
        if model in self._registry:
            raise AlreadyRegistered('The model %s is already registered' % model.__name__)
        
        self._registry[model] = index_class(model, self)
        self._setup_signals(model, self._registry[model])
    
    def unregister(self, model):
        """
        Unregisters a model from the site.
        """
        if model not in self._registry:
            raise NotRegistered('The model %s is not registered' % model.__name__)
        self._teardown_signals(model, self._registry[model])
        del(self._registry[model])
    
    def _setup_signals(self, model, index):
        signals.post_save.connect(index.update_object, sender=model)
        signals.post_delete.connect(index.remove_object, sender=model)
    
    def _teardown_signals(self, model, index):
        signals.post_save.disconnect(index.update_object, sender=model)
        signals.post_delete.disconnect(index.remove_object, sender=model)
    
    def get_index(self, model):
        """Provide the index that're being used for a particular model."""
        if model not in self._registry:
            raise NotRegistered('The model %s is not registered' % model.__name__)
        return self._registry[model]
    
    def get_indexes(self):
        """Provide a dict of all indexes that're being used."""
        return self._registry
    
    def get_indexed_models(self):
        """Provide a list of all models being indexed."""
        return self._registry.keys()
    
    def autodiscover(self):
        """
        Automatically build the site index.
        """
        # DRL_FIXME: Do we want to replicate NFA-like functionality on this?
        pass
