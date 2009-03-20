# "Hey, Django! Look at me, I'm an app! For Serious!"
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


# Not a Django model, but tightly tied to them and there doesn't seem to be a
# better spot in the tree.
class SearchResult(object):
    """
    A single search result. The actual object is loaded lazily by accessing
    object; until then this object only stores the model, pk, and score.
    
    Note that iterating over SearchResults and getting the object for each
    result will do O(N) database queries -- not such a great idea.
    """
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        self.app_label, self.module_name = app_label, model_name
        self.pk = pk
        self.score = score
        self._object = None
        self._model = None
        
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

    def content_type(self):
        return unicode(self.model._meta)


# DRL_FIXME: Not sure this works, but need something along these lines to make
#            sure the SearchSite(s) are loaded all the time (like the shell), not
#            just when hitting the website.
#            * This DOES work when running tests.
#            * This doesn't matter during web hits (loaded by URLconf).
#            * The only remaining bit to test is the shell and scripts.
# Make sure the site gets loaded.
def load_searchsite(sender, **kwargs):
    print "Checking the app cache..."
    
    if models.loading.app_cache_ready():
        import sys
        from django.conf import settings
        
        # Check to make sure it's not already loaded.
        if not settings.ROOT_URLCONF in sys.modules:
            print "Loading URLconf to initialize SearchSite..."
            __import__(settings.ROOT_URLCONF)

models.signals.class_prepared.connect(load_searchsite)
