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

    # DRL_FIME: Relevance removed.
    def search(self, query, models=None, order_by=None, limit=None, offset=None):
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


class BaseSearchQuery(object):
    """
    A base class for handling the query itself.
    
    This class acts as an intermediary between the SearchQuerySet and the
    search backend itself.
    
    Backends should extend this class and provide implementations for
    ``get_count``, ``build_query`` and ``clean``. See the ``solr`` backend
    for an example implementation.
    """
    
    def __init__(self, backend=None):
        self._query_keywords = []
        self.and_keywords = SortedDict()
        self.or_keywords = SortedDict()
        self.not_keywords = SortedDict()
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
        # DRL_FIXME: Argh. What to do about filters ('__') and how to internally store keywords.
        if not FILTER_SEPARATOR in expression:
            self._query_keywords.append(value)
        
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]
        
        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            lookup_type = 'exact'
        else:
            lookup_type = parts.pop()
        
        # DRL_FIXME: Using the dict/SortedDict sucks because the field can only appear once.
        #            Using a set sucks due to a lack of pairing of information and field only appears once.
        #            Using a list sucks due to a lack of pairing.
        #            Maybe a tree of term objects would be a solution?
        if not use_not and not use_or:
            self.and_keywords[field]
        elif use_not is True:
            self.not_keywords[field]
        elif use_or is True:
            self.or_keywords[field]
    
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
        clone.and_keywords = self.and_keywords
        clone.or_keywords = self.or_keywords
        clone.not_keywords = self.not_keywords
        clone.order_by = self.order_by
        clone.models = self.models
        clone.start_offset = self.start_offset
        clone.end_offset = self.end_offset
        clone.backend = self.backend
        return clone
