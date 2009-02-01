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
        self.model = models.get_model(app_label, model_name)
        self.pk = pk
        self.score = score
        self._object = None

    def __repr__(self):
        return "<SearchResult: %s(pk=%r)>" % (self.model.__name__, self.pk)

    def _get_object(self):
        if self._object is None:
            self._object = self.model._default_manager.get(pk=self.pk)
        return self._object
    
    def _set_object(self, obj):
        self._object = obj
    
    object = property(_get_object, _set_object)

    def content_type(self):
        return unicode(self.model._meta)
