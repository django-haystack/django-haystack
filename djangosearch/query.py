import djangosearch
from djangosearch.constants import REPR_OUTPUT_SIZE


# DRL_FIXME: Eventually support some sort of "or()" mechanism?
# DRL_TODO: Eventually support some sort of boost mechanism? (index time and search time)
class BaseSearchQuerySet(object):
    """
    Provides a way to specify search parameters and lazily load results.
    
    Supports chaining (a la QuerySet) to narrow the search.
    """
    def __init__(self, site=None, query=None):
        self.query = query or djangosearch.backend.SearchQuery()
        self._result_cache = None
        self._result_count = 0
        self._iter = None
        
        if site is not None:
            self.site = site
        else:
            self.site = djangosearch.site
    
    def __getstate__(self):
        """
        For pickling.
        """
        len(self)
        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict
    
    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)
    
    def __len__(self):
        # This needs to return the actual number of hits.
        if self._result_cache is None:
            self._result_count = self.query.get_count()
        return self._result_count
    
    def __iter__(self):
        # DRL_TODO: This may have to perform multiple queries as it goes into results that may not
        #           have been returned.
        pass
    
    # DRL_FIXME: This is cargo-culted from QuerySet. Adapt please.
    #            Once complete, SearchPaginator can go away as the only things
    #            it overrode will now be supported here.
    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            if self._iter is not None:
                # The result cache has only been partially populated, so we may
                # need to fill it out a bit more.
                if isinstance(k, slice):
                    if k.stop is not None:
                        # Some people insist on passing in strings here.
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.query.set_limits(start, stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.query.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist, e:
            raise IndexError, e.args
    
    
    # Methods that return a SearchQuerySet.
    
    def all(self):
        """Returns all results for the query."""
        return self._clone()
    
    def filter(self, **kwargs):
        """Narrows the search by looking for (and including) certain attributes."""
        clone = self._clone()
        for expression, value in kwargs.items():
            clone.query.add_filter(expression, value)
        return clone
    
    def exclude(self, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        for expression, value in kwargs.items():
            clone.query.add_filter(expression, value, use_not=True)
        return clone
    
    def order_by(self, field):
        clone = self._clone()
        clone.query.add_order_by(field)
        return clone
    
    def models(self, *models):
        """Accepts an arbitrary number of Model classes to include in the search."""
        clone = self._clone()
        for model in models:
            if model in self.site.get_indexed_models():
                clone.query.add_model(model)
        return clone
    
    def auto_query(self, query_string):
        """
        Performs a best guess constructing the search query.
        
        This method is somewhat naive but works well enough for the simple,
        common cases.
        """
        clone = self._clone()
        keywords = query_string.split()
        
        # Loop through keywords and add filters to the query.
        # DRL_FIXME: This is still *really* naive. Have a look at Google and
        #            see how their searches get expressed (because of
        #            familiarity for most users).
        #            Also, may need to support quotes on this.
        for keyword in keywords:
            cleaned_keyword = clone.query.clean(keyword)
            
            if cleaned_keyword.startswith('-'):
                clone.query.add_filter('content', cleaned_keyword, use_not=True)
            else:
                clone.query.add_filter('content', cleaned_keyword)
        
        return clone
    
    # Methods that do not return a SearchQuerySet.
    
    def count(self):
        """Returns the total number of matching results."""
        clone = self._clone()
        return len(clone)
    
    def best_match(self):
        """Returns the best/top search result that matches the query."""
        clone = self._clone()
        return clone[0]
    
    def latest(self, date_field):
        """Returns the most recent search result that matches the query."""
        clone = self._clone()
        clone.query.clear_order_by()
        clone.query.add_order_by("-%s" % date_field)
        return clone.best_match()
    
    
    # Utility methods.
    
    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        query = self.query._clone()
        clone = klass(site=self.site, query=query)
        return clone


# Build an instance. This should be acceptable, as it will almost always get
# cloned from and specialized in the clone.
SearchQuerySet = BaseSearchQuerySet()
