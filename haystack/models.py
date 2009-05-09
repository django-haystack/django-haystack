# "Hey, Django! Look at me, I'm an app! For Serious!"
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.encoding import force_unicode
from django.utils.text import capfirst


# Not a Django model, but tightly tied to them and there doesn't seem to be a
# better spot in the tree.
class SearchResult(object):
    """
    A single search result. The actual object is loaded lazily by accessing
    object; until then this object only stores the model, pk, and score.
    
    Note that iterating over SearchResults and getting the object for each
    result will do O(N) database queries -- not such a great idea.
    """
    def __init__(self, app_label, module_name, pk, score, **kwargs):
        self.app_label, self.module_name = app_label, module_name
        self.pk = pk
        self.score = score
        self._object = None
        self._model = None
        self._verbose_name = None
        
        for key, value in kwargs.items():
            if not key in self.__dict__:
                self.__dict__[key] = value

    def __repr__(self):
        return "<SearchResult: %s.%s (pk=%r)>" % (self.app_label, self.module_name, self.pk)
    
    def __getattr__(self, attr):
        return self.__dict__.get(attr, None)

    def _get_object(self):
        if self._object is None:
            try:
                self._object = self.model._default_manager.get(pk=self.pk)
            except ObjectDoesNotExist:
                self._object = None
        return self._object
    
    def _set_object(self, obj):
        self._object = obj
    
    object = property(_get_object, _set_object)
    
    def _get_model(self):
        if self._model is None:
            self._model = models.get_model(self.app_label, self.module_name)
        return self._model
    
    def _set_model(self, obj):
        self._model = obj
    
    model = property(_get_model, _set_model)
    
    def _get_verbose_name(self):
        return force_unicode(capfirst(self.model._meta.verbose_name))
    
    verbose_name = property(_get_verbose_name)

    def content_type(self):
        return unicode(self.model._meta)
