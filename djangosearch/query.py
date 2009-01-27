import djangosearch
from djangosearch.constants import REPR_OUTPUT_SIZE, ITERATOR_LOAD_PER_QUERY


# DRL_FIXME: Support some sort of "or()" method?
# DRL_FIXME: Support some sort of "more-like-this" method?
# DRL_TODO: Support some sort of "boost" method? (index time and search time)
# DRL_TODO: Add an "in_bulk" method (something along the lines of load_all from old djangosearch).
class BaseSearchQuerySet(object):
    """
    Provides a way to specify search parameters and lazily load results.
    
    Supports chaining (a la QuerySet) to narrow the search.
    """
    def __init__(self, site=None, query=None):
        self.query = query or djangosearch.backend.SearchQuery()
        self._result_cache = []
        self._result_count = None
        self._cache_full = False
        
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
        # This needs to return the actual number of hits, not what's in the cache.
        return self.query.get_count()
    
    def __iter__(self):
        if self._cache_is_full():
            # We've got a fully populated cache. Let Python do the hard work.
            return iter(self._result_cache)
        
        return self._manual_iter()
    
    def _cache_is_full(self):
        # Use ">=" because it's possible that search results have disappeared.
        return len(self._result_cache) >= len(self)
    
    def _manual_iter(self):
        # If we're here, our cache isn't fully populated.
        # For efficiency, fill the cache as we go if we run out of results.
        # Also, this can't be part of the __iter__ method due to Python's rules
        # about generator functions.
        current_position = 0
        
        while True:
            current_cache_max = len(self._result_cache)
            
            while current_position < current_cache_max:
                yield self._result_cache[current_position]
                current_position += 1
            
            if current_cache_max >= len(self):
                raise StopIteration
            
            # We've run out of results and haven't hit our limit.
            # Fill more of the cache.
            self._fill_cache()
    
    def _fill_cache(self):
        # Tell the query where to start from and how many we'd like.
        # DRL_FIXME: This seems ripe for off-by-one errors. Test it well.
        if self._result_cache is None:
            self._result_cache = []
        
        cache_length = len(self._result_cache)
        self.query.set_limits(cache_length, cache_length + ITERATOR_LOAD_PER_QUERY)
        
        for result in self.query.run():
            self._result_cache.append(result)
    
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
            if not self._cache_is_full():
                # We need check to see if we need to populate more of the cache.
                if isinstance(k, slice):
                    if k.stop is not None:
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                
                try:
                    while len(self._result_cache) < bound:
                        self._fill_cache()
                except StopIteration:
                    # There's nothing left, even though the bound is higher.
                    pass
            
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
        
        qs = self._clone()
        qs.query.set_limits(k, k + 1)
        return list(qs)[0]
    
    
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
