"""
A very basic, ORM-based backend for simple search during tests.
"""
from django.conf import settings
from django.db.models import Q
from haystack.backends import BaseSearchBackend, BaseSearchQuery, SearchNode, log_query
from haystack.models import SearchResult


BACKEND_NAME = 'simple'


if settings.DEBUG:
    import logging
    
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger('haystack.simple_backend')
    logger.setLevel(logging.WARNING)
    logger.addHandler(NullHandler())
    logger.addHandler(ch)


class SearchBackend(BaseSearchBackend):
    def update(self, indexer, iterable, commit=True):
        if settings.DEBUG:
            logger.warning('update is not implemented in this backend')
        pass
    
    def remove(self, obj, commit=True):
        if settings.DEBUG:
            logger.warning('remove is not implemented in this backend')
        pass
    
    def clear(self, models=[], commit=True):
        if settings.DEBUG:
            logger.warning('clear is not implemented in this backend')
        pass
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
        hits = 0
        results = []
        
        if result_class is None:
            result_class = SearchResult
        
        if query_string:
            for model in self.site.get_indexed_models():
                if query_string == '*':
                    qs = model.objects.all()
                else:
                    for term in query_string.split():
                        queries = []
                        
                        for field in model._meta._fields():
                            if hasattr(field, 'related'):
                                continue
                            
                            if not field.get_internal_type() in ('TextField', 'CharField', 'SlugField'):
                                continue
                            
                            queries.append(Q(**{'%s__icontains' % field.name: term}))
                        
                        qs = model.objects.filter(reduce(lambda x, y: x|y, queries))
                
                hits += len(qs)
                
                for match in qs:
                    result = result_class(match._meta.app_label, match._meta.module_name, match.pk, 0, **match.__dict__)
                    # For efficiency.
                    result._model = match.__class__
                    result._object = match
                    results.append(result)
        
        return {
            'results': results,
            'hits': hits,
        }
    
    def prep_value(self, db_field, value):
        return value
    
    def more_like_this(self, model_instance, additional_query_string=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=None, result_class=None, **kwargs):
        return {
            'results': [],
            'hits': 0
        }


class SearchQuery(BaseSearchQuery):
    def __init__(self, site=None, backend=None):
        super(SearchQuery, self).__init__(site, backend)
        
        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)
    
    def build_query(self):
        if not self.query_filter:
            return '*'
        
        return self._build_sub_query(self.query_filter)
    
    def _build_sub_query(self, search_node):
        term_list = []
        
        for child in search_node.children:
            if isinstance(child, SearchNode):
                term_list.append(self._build_query(child))
            else:
                term_list.append(child[1])
        
        return (' ').join(term_list)
