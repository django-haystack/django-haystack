# DRL_FIXME: Look at SoC branch for ideas about making this behave in
#            a QuerySet-like way. 
from itertools import islice
from django.db import models

class SearchResults(object):
    """
    Encapsulates some search results from a backend.
    
    Expects to be initalized with the original query string, an interator that
    yields "hits", the total number of hits, and a callback that will resolve
    those hits into (app_label, module_name, pk, score) tuples.
    """

    def __init__(self, query, iterator, hits, resolve_object_callback):
        self.query = query
        self.iterator = iterator
        self.hits = hits
        self.callback = resolve_object_callback

    def __iter__(self):
        for i in self.iterator:
            yield SearchResult(*self.callback(i))

    def __getitem__(self, k):
        """Get an item or slice from the result set."""
        if isinstance(k, slice):
            new_iter = islice(self.iterator, k.start, k.stop, k.step)
            return SearchResults(new_iter, self.callback)
        else:
            return list(islice(self.iterator, k, k+1))[0]

    def __repr__(self):
        return "<SearchResults for %r>" % self.query

    def load_all_results(self):
        """
        Load all result objects from the database.
        
        Returns a list of SearchResult objects with the object pre-loaded.
        
        This has better performance than the O(N) queries that iterating over
        the result set and doing ``result.object`` does; this does one
        ``in_bulk()`` call for each model in the result set.
        """
        original_results = []
        models_pks = {}

        # Remember the search position for each result so we don't have to resort later.
        for result in self:
            original_results.append(result)
            models_pks.setdefault(result.model, []).append(result.pk)

        # Load the objects for each model in turn
        loaded_objects = {}
        for model in models_pks:
            loaded_objects[model] = model._default_manager.in_bulk(models_pks[model])

        # Stick the result objects onto the SearchResult for returnage.
        for result in original_results:
            # We have to deal with integer keys being cast from strings; if this
            # fails we've got a character pk.
            try:
                result.pk = int(result.pk)
            except ValueError:
                pass
            try:
                result._object = loaded_objects[result.model][result.pk]
            except KeyError:
                # The object must have been deleted since we indexed; fail silently.
                continue

            yield result

class SearchResult(object):
    """
    A single search result. The actual object is loaded lazily by accessing
    object; until then this object only stores the model, pk, and score.
    
    Note that iterating over SearchResults and getting the object for each
    result will do O(N) database queries -- not such a great idea. If you know
    you need the whole result set, use SearchResults.load_all_results()
    instead.
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
    object = property(_get_object)

    def content_type(self):
        return unicode(self.model._meta)
