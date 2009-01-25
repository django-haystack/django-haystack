from django.db.models.base import ModelBase
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from djangosearch.constants import VALID_FILTERS, FILTER_SEPARATOR
try:
    set
except NameError:
    from sets import Set as set


class BaseSearchBackend(object):
    """
    Abstract search engine base class.
    """

    def get_identifier(self, obj):
        """
        Get an unique identifier for the object.

        If not overridden, uses <app_label>.<object_name>.<pk>.
        """
        return "%s.%s.%s" % (obj._meta.app_label, obj._meta.module_name, obj._get_pk_val())

    def update(self, indexer, iterable):
        raise NotImplementedError

    def remove(self, obj):
        raise NotImplementedError

    def clear(self, models):
        raise NotImplementedError

    def search(self, query):
        raise NotImplementedError

    def prep_value(self, db_field, value):
        """
        Hook to give the backend a chance to prep an attribute value before
        sending it to the search engine. By default, just force it to unicode.
        """
        return force_unicode(value)


# Alias for now.
# DRL_FIXME: Do I really want to do this? It makes loading the backend in
#            BaseSearchQuery clean but at what cost to clarity?
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
        
        return '<QueryFilter: %s %s=%s>' % (join, FILTER_SEPARATOR.join((self.field, self.filter_type)), self.value)
    
    def split_expression(self, expression):
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]
        
        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            filter_type = 'exact'
        else:
            filter_type = parts.pop()
        
        return (field, filter_type)
    
    def is_and(self):
        return not self.use_not and not self.use_or
    
    def is_not(self):
        return self.use_not
    
    def is_or(self):
        return self.use_or


class BaseSearchQuery(object):
    """
    A base class for handling the query itself.
    
    This class acts as an intermediary between the SearchQuerySet and the
    search backend itself.
    
    The SearchQuery object maintains a list of QueryFilter objects. Each filter
    object supports what field it looks up against, what kind of lookup (i.e. 
    the __'s), what value it's looking for and if it's a AND/OR/NOT. The
    SearchQuery's "_build_query" method should then iterate over that list and 
    convert that to a valid query for the search backend.
    
    Backends should extend this class and provide implementations for
    ``get_count``, ``build_query`` and ``clean``. See the ``solr`` backend
    for an example implementation.
    """
    
    def __init__(self, backend=None):
        self.query_filters = []
        self.order_by = []
        self.models = set()
        self.start_offset = 0
        self.end_offset = None
        self.backend = None
        
        if backend is not None:
            self.backend = backend()
        else:
            self.backend = SearchBackend()
    
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
        self.backend = SearchBackend()
    
    
    # Methods for backends to implement.
    
    def get_count(self):
        raise NotImplementedError("Subclasses must provide a way to return the total hits via the 'get_count' method.")
    
    def build_query(self):
        raise NotImplementedError("Subclasses must provide a way to generate the query via the 'build_query' method.")
    
    def clean(self, query_fragment):
        raise NotImplementedError("Subclasses must provide a way to sanitize a portion of the query via the 'clean' method.")
    
    
    # Standard methods to alter the query.
    
    def add_filter(self, expression, value, use_not=False, use_or=False):
        """Narrows the search by requiring certain conditions."""
        term = QueryFilter(expression, value, use_not, use_or)
        self.query_filters.append(term)
    
    def add_order_by(self, field):
        # DRL_TODO: Is this possible with most engines (beyond date ranking)?
        self.order_by.append(field)
    
    def clear_order_by(self):
        self.order_by = []
    
    def add_model(self, model):
        # DRL_FIXME: Too draconian? Is a class that quacks like a Model good enough?
        if not isinstance(model, ModelBase):
            raise AttributeError('The model being added to the query must derive from Model.')
        self.models.add(model)
    
    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        clone = klass()
        clone.query_filters = self.query_filters
        clone.order_by = self.order_by
        clone.models = self.models
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        clone.backend = self.backend
        return clone
