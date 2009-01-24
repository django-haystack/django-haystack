import djangosearch
try:
    set
except NameError:
    from sets import Set as set

# DRL_TODO: Mimic QuerySet as much as it makes sense to do here.
#           Allow for chaining, such as:
#           
#               SearchQuery.exclude(pub_date__lte=datetime.date(2008, 1, 16)).filter(content='lawrence')
#           
#           Eventually support some sort of "or()" mechanism?
#           Eventually support some sort of boost mechanism? (index time and search time)
#           
#           Ideally, when the query evaluates and performs a search, this should
#           return results itself to be iterated over (a la QuerySet).
#           
#           Also, figure out how best to load the backend here. It would be
#           useful for the query building as well as executing the query.


class BaseSearchQuery(object):
    # DRL_TODO: Figure out how to maintain the original query order.
    #           Also, can we use sets for the keywords?
    self.and_keywords = []
    self.or_keywords = []
    self.not_keywords = []
    self.order_by = []
    self.models = set()
    self.start_offset = 0
    self.end_offset = None
    self.backend = None
    
    def __init__(self, backend=None):
        if backend is not None:
            self.backend = backend()
        else:
            self.backend = djangosearch.backend.SearchBackend()
    
    def __str__(self):
        return self._build_query()
    
    def __getstate__(self):
        """
        For pickling.
        """
        obj_dict = self.__dict__.copy()
        del(obj_dict['backend'])
        return obj_dict
    
    def __setstate__(self, obj_dict):
        """
        For unpickling.
        """
        self.__dict__.update(obj_dict)
        # DRL_TODO: This may not unpickle properly if a different backend was supplied.
        self.backend = djangosearch.backend.SearchBackend()
    
    def get_count(self):
        raise NotImplementedError("Subclasses must provide a way to return the total hits via the get_count method.")
    
    def build_query(self):
        raise NotImplementedError("Subclasses must provide a way to generate the query.")
    
    # DRL_FIXME: The following 3 methods could probably be done better, especially
    #            given that all 3 will process expressions in the same way.
    #               - the field we're searching
    #               - what extension, if any, we're using
    #               - what the value ought to be
    #            Maybe we should have a Term/Filter object to encapsulate this?
    def add_and_keyword(self, keyword):
        self.and_keywords.append(keyword)
    
    def add_or_keyword(self, keyword):
        self.or_keywords.append(keyword)
    
    def add_not_keyword(self, keyword):
        self.not_keywords.append(keyword)
    
    def add_order_by(self, field):
        # DRL_TODO: Is this possible with most engines (beyond date ranking)?
        self.order_by.append(field)
    
    def clear_order_by(self):
        self.order_by = []
    
    def add_model(self, model):
        self.models.add(model)
    
    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        clone = klass()
        clone.and_keywords = self.and_keywords
        clone.or_keywords = self.or_keywords
        clone.not_keywords = self.not_keywords
        clone.order_by = self.order_by
        clone.models = self.models
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        clone.backend = self.backend
        return clone


class BaseSearchQuerySet(object):
    """
    Provides a way to specify search parameters and lazily load results.
    """
    def __init__(self, site=None, query=None):
        self.query = query or djangosearch.backend.SearchQuery()
        self._result_cache = None
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
        # DRL_FIXME: This should actually list out results, not print the query.
        return self.query
    
    def __len__(self):
        # DRL_TODO: This should track the full search hits instead of actual available results.
        pass
    
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
            clone.query.add_filter(expression, value, negate=True)
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
    
    def auto_query(self):
        """Performs a best guess constructing the search query."""
        clone = self._clone()
        # DRL_FIXME: Defer to backend to construct this? NO. Build it with the
        #            SearchQuerySet API, so there's only one path throught the
        #            SearchQuery.
        return clone
    
    # Methods that do not return a SearchQuerySet.
    
    def count(self):
        # For now, defer to the __len__ method, since we aren't likely to have
        # all results in memory.
        clone = self._clone()
        return len(clone)
    
    def best_match(self):
        # Return the top result. Get the iterator and return the first thing
        # we find.
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
        clone = klass(site=self.site)
        clone.and_keywords = self.and_keywords
        clone.or_keywords = self.or_keywords
        clone.not_keywords = self.not_keywords
        clone.order_by = self.order_by
        clone.models = self.models
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        return clone


# Build an instance. This should be acceptable, as it will almost always get
# cloned from and specialized in the clone.
# DRL_FIXME: Ensure all methods that should start with a clone have one.
SearchQuerySet = BaseSearchQuerySet()
