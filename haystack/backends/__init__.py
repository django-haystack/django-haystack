# -*- coding: utf-8 -*-
from copy import deepcopy
from time import time
from django.conf import settings
from django.core import signals
from django.db.models import Q
from django.db.models.base import ModelBase
from django.utils import tree
from django.utils.encoding import force_unicode
from haystack.constants import DJANGO_CT, VALID_FILTERS, FILTER_SEPARATOR
from haystack.exceptions import SearchBackendError, MoreLikeThisError, FacetingError
from haystack.models import SearchResult
try:
    set
except NameError:
    from sets import Set as set
try:
    from django.utils import importlib
except ImportError:
    from haystack.utils import importlib


VALID_GAPS = ['year', 'month', 'day', 'hour', 'minute', 'second']


# A means to inspect all search queries that have run in the last request.
queries = []


# Per-request, reset the ghetto query log.
# Probably not extraordinarily thread-safe but should only matter when
# DEBUG = True.
def reset_search_queries(**kwargs):
    global queries
    queries = []


if settings.DEBUG:
    signals.request_started.connect(reset_search_queries)


def log_query(func):
    """
    A decorator for pseudo-logging search queries. Used in the ``SearchBackend``
    to wrap the ``search`` method.
    """
    def wrapper(obj, query_string, *args, **kwargs):
        start = time()
        
        try:
            return func(obj, query_string, *args, **kwargs)
        finally:
            stop = time()
            
            if settings.DEBUG:
                global queries
                queries.append({
                    'query_string': query_string,
                    'additional_args': args,
                    'additional_kwargs': kwargs,
                    'time': "%.3f" % (stop - start),
                })
    
    return wrapper


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
    
    def clear(self, models=[], commit=True):
        """
        Clears the backend of all documents/objects for a collection of models.
        
        This method MUST be implemented by each backend, as it will be highly
        specific to each one.
        """
        raise NotImplementedError
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
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
    
    def more_like_this(self, model_instance, additional_query_string=None, result_class=None):
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
    
    def build_registered_models_list(self):
        """
        Builds a list of registered models for searching.
        
        The ``search`` method should use this and the ``django_ct`` field to
        narrow the results (unless the user indicates not to). This helps ignore
        any results that are not currently registered models and ensures
        consistent caching.
        """
        models = []
        
        for model in self.site.get_indexed_models():
            models.append(u"%s.%s" % (model._meta.app_label, model._meta.module_name))
        
        return models


# Alias for easy loading within SearchQuery objects.
SearchBackend = BaseSearchBackend


class SearchNode(tree.Node):
    """
    Manages an individual condition within a query.
    
    Most often, this will be a lookup to ensure that a certain word or phrase
    appears in the documents being indexed. However, it also supports filtering
    types (such as 'lt', 'gt', 'in' and others) for more complex lookups.
    
    This object creates a tree, with children being a list of either more
    ``SQ`` objects or the expressions/values themselves.
    """
    AND = 'AND'
    OR = 'OR'
    default = AND
    
    def __repr__(self):
        return '<SQ: %s %s>' % (self.connector, self.as_query_string(self._repr_query_fragment_callback))
    
    def _repr_query_fragment_callback(self, field, filter_type, value):
        return '%s%s%s=%s' % (field, FILTER_SEPARATOR, filter_type, force_unicode(value).encode('utf8'))
    
    def as_query_string(self, query_fragment_callback):
        """
        Produces a portion of the search query from the current SQ and its
        children.
        """
        result = []
        
        for child in self.children:
            if hasattr(child, 'as_query_string'):
                result.append(child.as_query_string(query_fragment_callback))
            else:
                expression, value = child
                field, filter_type = self.split_expression(expression)
                result.append(query_fragment_callback(field, filter_type, value))
        
        conn = ' %s ' % self.connector
        query_string = conn.join(result)
        
        if query_string:
            if self.negated:
                query_string = 'NOT (%s)' % query_string
            elif len(self.children) != 1:
                query_string = '(%s)' % query_string
        
        return query_string
    
    def split_expression(self, expression):
        """Parses an expression and determines the field and filter type."""
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]
        
        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            filter_type = 'exact'
        else:
            filter_type = parts.pop()
        
        return (field, filter_type)


class SQ(Q, SearchNode):
    """
    Manages an individual condition within a query.
    
    Most often, this will be a lookup to ensure that a certain word or phrase
    appears in the documents being indexed. However, it also supports filtering
    types (such as 'lt', 'gt', 'in' and others) for more complex lookups.
    """
    pass


class BaseSearchQuery(object):
    """
    A base class for handling the query itself.
    
    This class acts as an intermediary between the ``SearchQuerySet`` and the
    ``SearchBackend`` itself.
    
    The ``SearchQuery`` object maintains a tree of ``SQ`` objects. Each ``SQ``
    object supports what field it looks up against, what kind of lookup (i.e.
    the __'s), what value it's looking for, if it's a AND/OR/NOT and tracks
    any children it may have. The ``SearchQuery.build_query`` method starts with
    the root of the tree, building part of the final query at each node until
    the full final query is ready for the ``SearchBackend``.
    
    Backends should extend this class and provide implementations for
    ``build_query_fragment``, ``clean`` and ``run``. See the ``solr`` backend for an example
    implementation.
    """
    
    def __init__(self, site=None, backend=None):
        self.query_filter = SearchNode()
        self.order_by = []
        self.models = set()
        self.boost = {}
        self.start_offset = 0
        self.end_offset = None
        self.highlight = False
        self.facets = set()
        self.date_facets = {}
        self.query_facets = []
        self.narrow_queries = set()
        self._raw_query = None
        self._raw_query_params = {}
        self._more_like_this = False
        self._mlt_instance = None
        self._results = None
        self._hit_count = None
        self._facet_counts = None
        self._spelling_suggestion = None
        self.result_class = SearchResult
        
        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)
    
    def __str__(self):
        return self.build_query()
    
    def __getstate__(self):
        """For pickling."""
        obj_dict = self.__dict__.copy()
        del(obj_dict['backend'])
        
        # Rip off the class bits as we'll be using this path when we go to load
        # the backend.
        obj_dict['backend_used'] = ".".join(str(self.backend).replace("<", "").split(".")[0:-1])
        return obj_dict
    
    def __setstate__(self, obj_dict):
        """For unpickling."""
        backend_used = obj_dict.pop('backend_used')
        self.__dict__.update(obj_dict)
        
        try:
            loaded_backend = importlib.import_module(backend_used)
        except ImportError:
            raise SearchBackendError("The backend this query was pickled with '%s.SearchBackend' could not be loaded." % backend_used)
        
        self.backend = loaded_backend.SearchBackend()
    
    def has_run(self):
        """Indicates if any query has been been run."""
        return None not in (self._results, self._hit_count)
    
    def build_params(self, spelling_query=None):
        """Generates a list of params to use when searching."""
        kwargs = {
            'start_offset': self.start_offset,
        }
        
        if self.order_by:
            kwargs['sort_by'] = self.order_by
        
        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset
        
        if self.highlight:
            kwargs['highlight'] = self.highlight
        
        if self.facets:
            kwargs['facets'] = list(self.facets)
        
        if self.date_facets:
            kwargs['date_facets'] = self.date_facets
        
        if self.query_facets:
            kwargs['query_facets'] = self.query_facets
        
        if self.narrow_queries:
            kwargs['narrow_queries'] = self.narrow_queries
        
        if spelling_query:
            kwargs['spelling_query'] = spelling_query
        
        if self.boost:
            kwargs['boost'] = self.boost
        
        if self.result_class:
            kwargs['result_class'] = self.result_class
        
        return kwargs
    
    def run(self, spelling_query=None):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = self.build_params(spelling_query=spelling_query)
        
        results = self.backend.search(final_query, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
        self._facet_counts = self.post_process_facets(results)
        self._spelling_suggestion = results.get('spelling_suggestion', None)
    
    def run_mlt(self):
        """
        Executes the More Like This. Returns a list of search results similar
        to the provided document (and optionally query).
        """
        if self._more_like_this is False or self._mlt_instance is None:
            raise MoreLikeThisError("No instance was provided to determine 'More Like This' results.")
        
        kwargs = {
            'result_class': self.result_class,
        }
        
        additional_query_string = self.build_query()
        results = self.backend.more_like_this(self._mlt_instance, additional_query_string, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
    
    def run_raw(self):
        """Executes a raw query. Returns a list of search results."""
        kwargs = self.build_params()
        kwargs.update(self._raw_query_params)
        
        results = self.backend.search(self._raw_query, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
        self._facet_counts = results.get('facets', {})
        self._spelling_suggestion = results.get('spelling_suggestion', None)
    
    def get_count(self):
        """
        Returns the number of results the backend found for the query.
        
        If the query has not been run, this will execute the query and store
        the results.
        """
        if self._hit_count is None:
            # Limit the slice to 10 so we get a count without consuming
            # everything.
            if not self.end_offset:
                self.end_offset = 10
            
            if self._more_like_this:
                # Special case for MLT.
                self.run_mlt()
            elif self._raw_query:
                # Special case for raw queries.
                self.run_raw()
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
            elif self._raw_query:
                # Special case for raw queries.
                self.run_raw()
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
    
    def boost_fragment(self, boost_word, boost_value):
        """Generates query fragment for boosting a single word/value pair."""
        return "%s^%s" % (boost_word, boost_value)
    
    def matching_all_fragment(self):
        """Generates the query that matches all documents."""
        return '*'
    
    def build_query(self):
        """
        Interprets the collected query metadata and builds the final query to
        be sent to the backend.
        """
        query = self.query_filter.as_query_string(self.build_query_fragment)
        
        if not query:
            # Match all.
            query = self.matching_all_fragment()
        
        if len(self.models):
            models = sorted(['%s:%s.%s' % (DJANGO_CT, model._meta.app_label, model._meta.module_name) for model in self.models])
            models_clause = ' OR '.join(models)
            
            if query != self.matching_all_fragment():
                final_query = '(%s) AND (%s)' % (query, models_clause)
            else:
                final_query = models_clause
        else:
            final_query = query
        
        if self.boost:
            boost_list = []
            
            for boost_word, boost_value in self.boost.items():
                boost_list.append(self.boost_fragment(boost_word, boost_value))
            
            final_query = "%s %s" % (final_query, " ".join(boost_list))
        
        return final_query
    
    def combine(self, rhs, connector=SQ.AND):
        if connector == SQ.AND:
            self.add_filter(rhs.query_filter)
        elif connector == SQ.OR:
            self.add_filter(rhs.query_filter, use_or=True)
    
    # Methods for backends to implement.
    
    def build_query_fragment(self, field, filter_type, value):
        """
        Generates a query fragment from a field, filter type and a value.
        
        Must be implemented in backends as this will be highly backend specific.
        """
        raise NotImplementedError("Subclasses must provide a way to generate query fragments via the 'build_query_fragment' method.")
    
    
    # Standard methods to alter the query.
    
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
    
    def add_filter(self, query_filter, use_or=False):
        """
        Adds a SQ to the current query.
        """
        # TODO: consider supporting add_to_query callbacks on q objects
        if use_or:
            connector = SQ.OR
        else:
            connector = SQ.AND
        
        if self.query_filter and query_filter.connector != SQ.AND and len(query_filter) > 1:
            self.query_filter.start_subtree(connector)
            subtree = True
        else:
            subtree = False
        
        for child in query_filter.children:
            if isinstance(child, tree.Node):
                self.query_filter.start_subtree(connector)
                self.add_filter(child)
                self.query_filter.end_subtree()
            else:
                expression, value = child
                self.query_filter.add((expression, value), connector)
            
            connector = query_filter.connector
        
        if query_filter.negated:
            self.query_filter.negate()
        
        if subtree:
            self.query_filter.end_subtree()
    
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
        
        This method causes the SearchQuery to ignore the standard query
        generating facilities, running only what was provided instead.
        
        Note that any kwargs passed along will override anything provided
        to the rest of the ``SearchQuerySet``.
        """
        self._raw_query = query_string
        self._raw_query_params = kwargs
    
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
        self.facets.add(self.backend.site.get_facet_field_name(field))
    
    def add_date_facet(self, field, start_date, end_date, gap_by, gap_amount=1):
        """Adds a date-based facet on a field."""
        if not gap_by in VALID_GAPS:
            raise FacetingError("The gap_by ('%s') must be one of the following: %s." % (gap_by, ', '.join(VALID_GAPS)))
        
        details = {
            'start_date': start_date,
            'end_date': end_date,
            'gap_by': gap_by,
            'gap_amount': gap_amount,
        }
        self.date_facets[self.backend.site.get_facet_field_name(field)] = details
    
    def add_query_facet(self, field, query):
        """Adds a query facet on a field."""
        self.query_facets.append((self.backend.site.get_facet_field_name(field), query))
    
    def add_narrow_query(self, query):
        """
        Narrows a search to a subset of all documents per the query.
        
        Generally used in conjunction with faceting.
        """
        self.narrow_queries.add(query)
    
    def set_result_class(self, klass):
        """
        Sets the result class to use for results.
        
        Overrides any previous usages. If ``None`` is provided, Haystack will
        revert back to the default ``SearchResult`` object.
        """
        if klass is None:
            klass = SearchResult
        
        self.result_class = klass
    
    def post_process_facets(self, results):
        # Handle renaming the facet fields. Undecorate and all that.
        revised_facets = {}
        field_data = self.backend.site.all_searchfields()
        
        for facet_type, field_details in results.get('facets', {}).items():
            temp_facets = {}
            
            for field, field_facets in field_details.items():
                fieldname = field
                if field in field_data and hasattr(field_data[field], 'get_facet_for_name'):
                    fieldname = field_data[field].get_facet_for_name()
                
                temp_facets[fieldname] = field_facets
            
            revised_facets[facet_type] = temp_facets
        
        return revised_facets
    
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
        clone.query_filter = deepcopy(self.query_filter)
        clone.order_by = self.order_by[:]
        clone.models = self.models.copy()
        clone.boost = self.boost.copy()
        clone.highlight = self.highlight
        clone.facets = self.facets.copy()
        clone.date_facets = self.date_facets.copy()
        clone.query_facets = self.query_facets[:]
        clone.narrow_queries = self.narrow_queries.copy()
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        clone.backend = self.backend
        clone.result_class = self.result_class
        clone._raw_query = self._raw_query
        clone._raw_query_params = self._raw_query_params
        return clone
