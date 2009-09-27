import re
from django.conf import settings
from haystack import backend
from haystack.constants import REPR_OUTPUT_SIZE, ITERATOR_LOAD_PER_QUERY, DEFAULT_OPERATOR
from haystack.exceptions import NotRegistered


class SearchQuerySet(object):
    """
    Provides a way to specify search parameters and lazily load results.
    
    Supports chaining (a la QuerySet) to narrow the search.
    """
    def __init__(self, site=None, query=None):
        self.query = query or backend.SearchQuery()
        self._result_cache = []
        self._result_count = None
        self._cache_full = False
        self._load_all = False
        self._load_all_querysets = {}
        self._ignored_result_count = 0
        
        if site is not None:
            self.site = site
        else:
            from haystack import site as main_site
            self.site = main_site
    
    def __getstate__(self):
        """
        For pickling.
        """
        len(self)
        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict
    
    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE])
        
        if len(self) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        
        return repr(data)
    
    def __len__(self):
        # This needs to return the actual number of hits, not what's in the cache.
        # DRL_FIXME: Should we take into account the ignored results here?
        return self.query.get_count()
    
    def __iter__(self):
        if self._cache_is_full():
            # We've got a fully populated cache. Let Python do the hard work.
            return iter(self._result_cache)
        
        return self._manual_iter()
    
    def _cache_is_full(self):
        # Use ">=" because it's possible that search results have disappeared.
        return len(self._result_cache) >= len(self) - self._ignored_result_count
    
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
            
            if self._cache_is_full():
                raise StopIteration
            
            # We've run out of results and haven't hit our limit.
            # Fill more of the cache.
            self._fill_cache()
    
    def _fill_cache(self):
        from haystack import site
        
        if self._result_cache is None:
            self._result_cache = []
        
        # Tell the query where to start from and how many we'd like.
        cache_length = len(self._result_cache)
        self.query._reset()
        self.query.set_limits(cache_length, cache_length + ITERATOR_LOAD_PER_QUERY)
        results = self.query.get_results()
        
        # Check if we wish to load all objects.
        if self._load_all:
            original_results = []
            models_pks = {}
            loaded_objects = {}
            
            # Remember the search position for each result so we don't have to resort later.
            for result in results:
                original_results.append(result)
                models_pks.setdefault(result.model, []).append(result.pk)
            
            # Load the objects for each model in turn.
            for model in models_pks:
                if model in self._load_all_querysets:
                    # Use the overriding queryset.
                    loaded_objects[model] = self._load_all_querysets[model].in_bulk(models_pks[model])
                else:
                    # Check the SearchIndex for the model for an override.
                    try:
                        index = site.get_index(model)
                        qs = index.load_all_queryset()
                        loaded_objects[model] = qs.in_bulk(models_pks[model])
                    except NotRegistered:
                        # The model returned doesn't seem to be registered with
                        # the current site. We should silently fail and populate
                        # nothing for those objects.
                        loaded_objects[model] = []
        
        if len(results) < ITERATOR_LOAD_PER_QUERY:
            self._ignored_result_count += ITERATOR_LOAD_PER_QUERY - len(results)
        
        for result in results:
            if self._load_all:
                # We have to deal with integer keys being cast from strings; if this
                # fails we've got a character pk.
                try:
                    result.pk = int(result.pk)
                except ValueError:
                    pass
                try:
                    result._object = loaded_objects[result.model][result.pk]
                except (KeyError, IndexError):
                    # The object was either deleted since we indexed or should
                    # be ignored; fail silently.
                    self._ignored_result_count += 1
                    continue
            
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
                    while len(self._result_cache) < bound and not self._cache_is_full():
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
    
    def none(self):
        """Returns all results for the query."""
        return self._clone(klass=EmptySearchQuerySet)
    
    def filter(self, **kwargs):
        """Narrows the search based on certain attributes and the default operator."""
        if getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', DEFAULT_OPERATOR) == 'OR':
            return self.filter_or(**kwargs)
        else:
            return self.filter_and(**kwargs)
    
    def exclude(self, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        
        for expression, value in kwargs.items():
            clone.query.add_filter(expression, value, use_not=True)
        
        return clone
    
    def filter_and(self, **kwargs):
        """Narrows the search by looking for (and including) certain attributes."""
        clone = self._clone()
        
        for expression, value in kwargs.items():
            clone.query.add_filter(expression, value)
        
        return clone
    
    def filter_or(self, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        
        for expression, value in kwargs.items():
            clone.query.add_filter(expression, value, use_or=True)
        
        return clone
    
    def order_by(self, *args):
        """Alters the order in which the results should appear."""
        clone = self._clone()
        
        for field in args:
            clone.query.add_order_by(field)
        
        return clone
    
    def highlight(self):
        """Adds highlighting to the results."""
        clone = self._clone()
        clone.query.add_highlight()
        return clone
    
    def models(self, *models):
        """Accepts an arbitrary number of Model classes to include in the search."""
        clone = self._clone()
        
        for model in models:
            if model in self.site.get_indexed_models():
                clone.query.add_model(model)
        
        return clone
    
    def boost(self, term, boost):
        """Boosts a certain aspect of the query."""
        clone = self._clone()
        clone.query.add_boost(term, boost)
        return clone
    
    def facet(self, field):
        """Adds faceting to a query for the provided field."""
        clone = self._clone()
        clone.query.add_field_facet(field)
        return clone
    
    def date_facet(self, field, start_date, end_date, gap_by, gap_amount=1):
        """Adds faceting to a query for the provided field by date."""
        clone = self._clone()
        clone.query.add_date_facet(field, start_date, end_date, gap_by, gap_amount=gap_amount)
        return clone
    
    def query_facet(self, field, query):
        """Adds faceting to a query for the provided field with a custom query."""
        clone = self._clone()
        clone.query.add_query_facet(field, query)
        return clone
    
    def narrow(self, query):
        """Pushes existing facet choices into the search."""
        clone = self._clone()
        clone.query.add_narrow_query(query)
        return clone
    
    # DRL_TODO: Should this prevent other methods (filter/exclude/etc) from working?
    def raw_search(self, query_string, **kwargs):
        """Passes a raw query directly to the backend."""
        clone = self._clone()
        clone.query.raw_search(query_string, **kwargs)
        return clone
    
    def load_all(self):
        """Efficiently populates the objects in the search results."""
        clone = self._clone()
        clone._load_all = True
        return clone
    
    def load_all_queryset(self, model, queryset):
        """
        Allows for specifying a custom ``QuerySet`` that changes how ``load_all``
        will fetch records for the provided model.
        
        This is useful for post-processing the results from the query, enabling
        things like adding ``select_related`` or filtering certain data.
        """
        clone = self._clone()
        clone._load_all_querysets[model] = queryset
        return clone
    
    def auto_query(self, query_string):
        """
        Performs a best guess constructing the search query.
        
        This method is somewhat naive but works well enough for the simple,
        common cases.
        """
        clone = self._clone()
        
        # Pull out anything wrapped in quotes and do an exact match on it.
        quote_regex = re.compile(r'([\'"])(.*?)\1')
        result = quote_regex.search(query_string)
        
        while result is not None:
            full_match = result.group()
            query_string = query_string.replace(full_match, '', 1)
            
            exact_match = result.groups()[1]
            clone = clone.filter(content=exact_match)
            
            # Re-search the string for other exact matches.
            result = quote_regex.search(query_string)
        
        # Pseudo-tokenize the rest of the query.
        keywords = query_string.split()
        
        # Loop through keywords and add filters to the query.
        for keyword in keywords:
            exclude = False
            
            if keyword.startswith('-') and len(keyword) > 1:
                keyword = keyword[1:]
                exclude = True
            
            cleaned_keyword = clone.query.clean(keyword)
            
            if exclude:
                clone = clone.exclude(content=cleaned_keyword)
            else:
                clone = clone.filter(content=cleaned_keyword)
        
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
    
    def more_like_this(self, model_instance):
        """Finds similar results to the object passed in."""
        clone = self._clone()
        clone.query.more_like_this(model_instance)
        return clone
    
    def facet_counts(self):
        """
        Returns the facet counts found by the query.
        
        This will cause the query to execute and should generally be used when
        presenting the data.
        """
        clone = self._clone()
        return clone.query.get_facet_counts()
    
    def spelling_suggestion(self, preferred_query=None):
        """
        Returns the spelling suggestion found by the query.
        
        To work, you must set ``settings.HAYSTACK_INCLUDE_SPELLING`` to True.
        Otherwise, ``None`` will be returned.
        
        This will cause the query to execute and should generally be used when
        presenting the data.
        """
        clone = self._clone()
        return clone.query.get_spelling_suggestion(preferred_query)
    
    
    # Utility methods.
    
    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        
        query = self.query._clone()
        clone = klass(site=self.site, query=query)
        clone._load_all = self._load_all
        clone._load_all_querysets = self._load_all_querysets
        return clone


class EmptySearchQuerySet(SearchQuerySet):
    """
    A stubbed SearchQuerySet that behaves as normal but always returns no
    results.
    """
    def __len__(self):
        return 0
    
    def _cache_is_full(self):
        # Pretend the cache is always full with no results.
        return True
    
    def _clone(self, klass=None):
        clone = super(EmptySearchQuerySet, self)._clone(klass=klass)
        clone._result_cache = []
        return clone
