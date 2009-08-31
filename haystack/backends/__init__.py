# -*- coding: utf-8 -*-
import re
from django.db.models.base import ModelBase
from django.utils.encoding import force_unicode
from haystack.constants import VALID_FILTERS, FILTER_SEPARATOR
from haystack.exceptions import SearchBackendError, MoreLikeThisError, FacetingError
try:
    set
except NameError:
    from sets import Set as set


IDENTIFIER_REGEX = re.compile('^[\w\d_]+\.[\w\d_]+\.\d+$')
VALID_GAPS = ['year', 'month', 'day', 'hour', 'minute', 'second']


class BaseSearchBackend(object):
    # Backends should include their own reserved words/characters.
    RESERVED_WORDS = []
    RESERVED_CHARACTERS = []
    
    """
    Abstract search engine base class.
    """
    def __init__(self, site=None):
        if site is not None:
            self.site = site
        else:
            from haystack import site
            self.site = site
    
    def get_identifier(self, obj_or_string):
        """
        Get an unique identifier for the object or a string representing the
        object.

        If not overridden, uses <app_label>.<object_name>.<pk>.
        """
        if isinstance(obj_or_string, basestring):
            if not IDENTIFIER_REGEX.match(obj_or_string):
                raise AttributeError("Provided string '%s' is not a valid identifier." % obj_or_string)
            
            return obj_or_string
        
        return u"%s.%s.%s" % (obj_or_string._meta.app_label, obj_or_string._meta.module_name, obj_or_string._get_pk_val())

    def update(self, index, iterable):
        """
        Updates the backend when given a SearchIndex and a collection of
        documents.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError

    def remove(self, obj_or_string):
        """
        Removes a document/object from the backend. Can be either a model
        instance or the identifier (i.e. ``app_name.model_name.id``) in the
        event the object no longer exists.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError

    def clear(self, models=[]):
        """
        Clears the backend of all documents/objects for a collection of models.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError

    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None, **kwargs):
        """
        Takes a query to search on and returns dictionary.
        
        The query should be a string that is appropriate syntax for the backend.
        
        The returned dictionary should contain the keys 'results' and 'hits'.
        The 'results' value should be an iterable of populated SearchResult
        objects. The 'hits' should be an integer count of the number of matched
        results the search backend found.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError

    def prep_value(self, value):
        """
        Hook to give the backend a chance to prep an attribute value before
        sending it to the search engine. By default, just force it to unicode.
        """
        return force_unicode(value)
    
    def more_like_this(self, model_instance, additional_query_string=None):
        """
        Takes a model object and returns results the backend thinks are similar.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError("Subclasses must provide a way to fetch similar record via the 'more_like_this' method if supported by the backend.")
    
    def build_schema(self, fields):
        """
        Takes a dictionary of fields and returns schema information.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError("Subclasses must provide a way to build their schema.")


# Alias for easy loading within SearchQuery objects.
SearchBackend = BaseSearchBackend


class QueryFilter(object):
    """
    Manages an individual condition within a query.
    
    Most often, this will be a lookup to ensure that a certain word or phrase
    appears in the documents being indexed. However, it also supports filtering
    types (such as 'lt', 'gt', 'in' and others) for more complex lookups.
    """
    def __init__(self, expression, value, use_not=False, use_or=False):
        self.field, self.filter_type = self.split_expression(expression)
        self.value = value
        
        if use_not and use_or:
            raise AttributeError("Query filters can not accept both NOT and OR.")
        
        self.use_not = use_not
        self.use_or = use_or
    
    def __repr__(self):
        join = 'AND'
        
        if self.is_not():
            join = 'NOT'
        
        if self.is_or():
            join = 'OR'
        
        return '<QueryFilter: %s %s=%s>' % (join, FILTER_SEPARATOR.join((self.field, self.filter_type)), force_unicode(self.value).encode('utf8'))
    
    def split_expression(self, expression):
        """Parses an expression and determines the field and filter type."""
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]
        
        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            filter_type = 'exact'
        else:
            filter_type = parts.pop()
        
        return (field, filter_type)
    
    def is_and(self):
        """
        A shortcut to determine if the filter is to be attached to the rest
        of the query using 'AND'.
        """
        return not self.use_not and not self.use_or
    
    def is_not(self):
        """
        A shortcut to determine if the filter is to be attached to the rest
        of the query using 'NOT'.
        """
        return self.use_not
    
    def is_or(self):
        """
        A shortcut to determine if the filter is to be attached to the rest
        of the query using 'OR'.
        """
        return self.use_or


class BaseSearchQuery(object):
    """
    A base class for handling the query itself.
    
    This class acts as an intermediary between the SearchQuerySet and the
    search backend itself.
    
    The SearchQuery object maintains a list of QueryFilter objects. Each filter
    object supports what field it looks up against, what kind of lookup (i.e. 
    the __'s), what value it's looking for and if it's a AND/OR/NOT. The
    SearchQuery's "build_query" method should then iterate over that list and 
    convert that to a valid query for the search backend.
    
    Backends should extend this class and provide implementations for
    ``build_query``, ``clean`` and ``run``. See the ``solr`` backend
    for an example implementation.
    """
    
    def __init__(self, backend=None):
        self.query_filters = []
        self.order_by = []
        self.models = set()
        self.boost = {}
        self.start_offset = 0
        self.end_offset = None
        self.highlight = False
        self.facets = set()
        self.date_facets = {}
        self.query_facets = {}
        self.narrow_queries = set()
        self._more_like_this = False
        self._mlt_instance = None
        self._results = None
        self._hit_count = None
        self._facet_counts = None
        self._spelling_suggestion = None
        self.backend = backend or SearchBackend()
    
    def __str__(self):
        return self.build_query()
    
    def __getstate__(self):
        """For pickling."""
        obj_dict = self.__dict__.copy()
        del(obj_dict['backend'])
        # Rip off the class bits as we'll be using this path when we go to load
        # the backend.
        obj_dict['backend_used'] = ".".join(str(self.backend).replace("<class '", "").replace("'>", "").split(".")[0:-1])
        return obj_dict
    
    def __setstate__(self, obj_dict):
        """For unpickling."""
        backend_used = obj_dict.pop('backend_used')
        self.__dict__.update(obj_dict)
        
        try:
            loaded_backend = __import__(backend_used)
        except ImportError:
            raise SearchBackendError("The backend this query was pickled with '%s.SearchBackend' could not be loaded." % backend_used)
        
        self.backend = loaded_backend.SearchBackend()
    
    def run(self, spelling_query=None):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        results = self.backend.search(final_query, highlight=self.highlight, spelling_query=spelling_query)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
        self._facet_counts = results.get('facets', {})
        self._spelling_suggestion = results.get('spelling_suggestion', None)
    
    def run_mlt(self):
        """
        Executes the More Like This. Returns a list of search results similar
        to the provided document (and optionally query).
        """
        if self._more_like_this is False or self._mlt_instance is None:
            raise MoreLikeThisError("No instance was provided to determine 'More Like This' results.")
        
        additional_query_string = self.build_query()
        results = self.backend.more_like_this(self._mlt_instance, additional_query_string)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
    
    def get_count(self):
        """
        Returns the number of results the backend found for the query.
        
        If the query has not been run, this will execute the query and store
        the results.
        """
        if self._hit_count is None:
            if self._more_like_this:
                # Special case for MLT.
                self.run_mlt()
            else:
                self.run()
        
        return self._hit_count
    
    def get_results(self):
        """
        Returns the results received from the backend.
        
        If the query has not been run, this will execute the query and store
        the results.
        """
        if self._results is None:
            if self._more_like_this:
                # Special case for MLT.
                self.run_mlt()
            else:
                self.run()
        
        return self._results
    
    def get_facet_counts(self):
        """
        Returns the facet counts received from the backend.
        
        If the query has not been run, this will execute the query and store
        the results.
        """
        if self._facet_counts is None:
            self.run()
        
        return self._facet_counts
    
    def get_spelling_suggestion(self, preferred_query=None):
        """
        Returns the spelling suggestion received from the backend.
        
        If the query has not been run, this will execute the query and store
        the results.
        """
        if self._spelling_suggestion is None:
            self.run(spelling_query=preferred_query)
        
        return self._spelling_suggestion
    
    
    # Methods for backends to implement.
    
    def build_query(self):
        """
        Interprets the collected query metadata and builds the final query to
        be sent to the backend.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError("Subclasses must provide a way to generate the query via the 'build_query' method.")
    
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.
        
        A basic (override-able) implementation is provided.
        """
        words = query_fragment.split()
        cleaned_words = []
        
        for word in words:
            if word in self.backend.RESERVED_WORDS:
                word = word.replace(word, word.lower())
        
            for char in self.backend.RESERVED_CHARACTERS:
                word = word.replace(char, '\\%s' % char)
            
            cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    
    # Standard methods to alter the query.
    
    def add_filter(self, expression, value, use_not=False, use_or=False):
        """Narrows the search by requiring certain conditions."""
        term = QueryFilter(expression, value, use_not, use_or)
        self.query_filters.append(term)
    
    def add_order_by(self, field):
        """Orders the search result by a field."""
        self.order_by.append(field)
    
    def clear_order_by(self):
        """
        Clears out all ordering that has been already added, reverting the
        query to relevancy.
        """
        self.order_by = []
    
    def add_model(self, model):
        """
        Restricts the query requiring matches in the given model.
        
        This builds upon previous additions, so you can limit to multiple models
        by chaining this method several times.
        """
        if not isinstance(model, ModelBase):
            raise AttributeError('The model being added to the query must derive from Model.')
        self.models.add(model)
    
    def set_limits(self, low=None, high=None):
        """Restricts the query by altering either the start, end or both offsets."""
        if low is not None:
            self.start_offset = int(low)
        
        if high is not None:
            self.end_offset = int(high)
    
    def clear_limits(self):
        """Clears any existing limits."""
        self.start_offset, self.end_offset = 0, None
    
    def add_boost(self, term, boost_value):
        """Adds a boosted term and the amount to boost it to the query."""
        self.boost[term] = boost_value
    
    def raw_search(self, query_string, **kwargs):
        """
        Runs a raw query (no parsing) against the backend.
        
        This method does not affect the internal state of the SearchQuery used
        to build queries. It does however populate the results/hit_count.
        """
        results = self.backend.search(query_string, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
    
    def more_like_this(self, model_instance):
        """
        Allows backends with support for "More Like This" to return results
        similar to the provided instance.
        """
        self._more_like_this = True
        self._mlt_instance = model_instance
    
    def add_highlight(self):
        """Adds highlighting to the search results."""
        self.highlight = True
    
    def add_field_facet(self, field):
        """Adds a regular facet on a field."""
        self.facets.add(field)
    
    def add_date_facet(self, field, start_date, end_date, gap_by, gap_amount=1):
        """Adds a date-based facet on a field."""
        if not gap_by in VALID_GAPS:
            raise FacetingError("The gap_by ('%s') must be one of the following: %s." (gap_by, ', '.join(VALID_GAPS)))
        
        details = {
            'start_date': start_date,
            'end_date': end_date,
            'gap_by': gap_by,
            'gap_amount': gap_amount,
        }
        self.date_facets[field] = details
    
    def add_query_facet(self, field, query):
        """Adds a query facet on a field."""
        self.query_facets[field] = query
    
    def add_narrow_query(self, query):
        """Adds a existing facet on a field."""
        self.narrow_queries.add(query)
    
    def _reset(self):
        """
        Resets the instance's internal state to appear as though no query has
        been run before. Only need to tweak a few variables we check.
        """
        self._results = None
        self._hit_count = None
        self._facet_counts = None
        self._spelling_suggestion = None
    
    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        
        clone = klass()
        clone.query_filters = self.query_filters[:]
        clone.order_by = self.order_by[:]
        clone.models = self.models.copy()
        clone.boost = self.boost.copy()
        clone.highlight = self.highlight
        clone.facets = self.facets.copy()
        clone.date_facets = self.date_facets.copy()
        clone.query_facets = self.query_facets.copy()
        clone.narrow_queries = self.narrow_queries.copy()
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        clone.backend = self.backend
        return clone
