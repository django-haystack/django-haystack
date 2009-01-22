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

class SearchQuerySet(object):
    """
    Lazily generates the query to be sent to the backend.
    """
    def __init__(self, site=None):
        self._completed_query = None
        self.and_keywords = set()
        self.or_keywords = set()
        self.not_keywords = set()
        self.order_by = []
        self.models = set()
        self.start_offset = 0
        self.end_offset = None
        
        if site:
            self.site = site
        else:
            self.site = djangosearch.site
    
    def __getstate__(self):
        """
        For pickling.
        """
        len(self)
        obj_dict = self.__dict__.copy()
        # DRL_FIXME: Remove backend details as necessary.
        return obj_dict
    
    def __setstate__(self, obj_dict):
        """
        For unpickling.
        """
        self.__dict__.update(obj_dict)
        # DRL_FIXME: Reestablish backend details here.
    
    def __repr__(self):
        if self._complete_query is None:
            self._complete_query = self._build_query()
        return self._complete_query
    
    def __len__(self):
        # DRL_TODO: This should track the full search hits instead of actual available results.
        pass
    
    def __iter__(self):
        # DRL_TODO: This may have to perform multiple queries as it goes into results that may not
        #           have been returned.
        pass
    
    def _build_query(self):
        # This will have to be implemented by each backend.
        # DRL_TODO: Is there a better way to do this than force everyone to implement?
        # DRL_TODO: Determine what "__" extensions to include.
        raise NotImplemented("Each search backend must define it's own _build_query method.")
    
    
    # Methods that return a SearchQuerySet.
    
    def all(self):
        """Returns all results for the query."""
        # This is largely backend specific.
        # DRL_FIXME: This will need to no-op if there's any query data.
        clone = self._clone()
        return clone
    
    def none(self):
        clone = self.clone()
        clone.and_keywords = set()
        clone.or_keywords = set()
        clone.not_keywords = set()
        clone.order_by = []
        clone.models = set()
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        return clone
    
    def filter(self, **kwargs):
        """Narrows the search by looking for (and including) certain attributes."""
        clone = self._clone()
        for key, value in kwargs.items():
            # DRL_FIXME: Not sure what to do here. We need to track multiple things:
            #   - the field we're searching
            #   - what extension, if any, we're using
            #   - what the value ought to be
            # Maybe we should have a Term/Filter object to encapsulate this?
            pass
        return clone
    
    def exclude(self, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        for key, value in kwargs.items():
            # DRL_FIXME: Same problem as filter.
            pass
        return clone
    
    def order_by(self, field):
        # DRL_TODO: Is this possible with most engines (beyond date ranking)?
        clone = self._clone()
        self.order_by.append(field)
        return clone
    
    def models(self, *models):
        """Accepts an arbitrary number of Model classes to include in the search."""
        clone = self._clone()
        for model in models:
            if model in self.site.get_indexed_models():
                clone.models.add(model)
        return clone
    
    # Methods that do not return a SearchQuerySet.
    
    def count(self):
        # For now, defer to the __len__ method, since we aren't likely to have
        # all results in memory.
        return len(self)
    
    def best_match(self):
        # Return the top result. Get the iterator and return the first thing
        # we find.
        pass
    
    def latest(self, date_field):
        """Returns the most recent search result that matches the query."""
        self.order_by("-%s" % date_field)
        return self.best_match()
    
    
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
    