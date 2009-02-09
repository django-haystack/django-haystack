# "Hey, Django! Look at me, I'm an app! For Serious!"
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
    def __init__(self, app_label, model_name, pk, score):
        self.app_label, self.module_name = app_label, model_name
        self.model = models.get_model(app_label, model_name)
        self.pk = pk
        self.score = score
        self._object = None

    def __repr__(self):
        return "<SearchResult: %s.%s (pk=%r)>" % (self.app_label, self.module_name, self.pk)

    def _get_object(self):
        if self._object is None:
            self._object = self.model._default_manager.get(pk=self.pk)
        return self._object
    
    def _set_object(self, obj):
        self._object = obj
    
    object = property(_get_object, _set_object)

    def content_type(self):
        return unicode(self.model._meta)


# DRL_FIME: Not sure this works, but need something along these lines to make
#           sure the SearchIndex(s) are loaded all the time (like the shell), not
#           just when hitting the website.
# Make sure the index gets loaded.
def load_indexsite(sender, **kwargs):
    print "Checking the app cache..."
    
    if models.loading.app_cache_ready():
        import sys
        from django.conf import settings
        
        # Check to make sure it's not already loaded.
        if not settings.ROOT_URLCONF in sys.modules:
            print "Loading URLconf to initialize SearchIndex..."
            __import__(settings.ROOT_URLCONF)

models.signals.class_prepared.connect(load_indexsite)
