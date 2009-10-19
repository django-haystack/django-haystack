"""
A fake backend for dummying during tests.
"""
from haystack.backends import BaseSearchBackend, BaseSearchQuery, log_query
from haystack.constants import FILTER_SEPARATOR
from haystack.models import SearchResult


BACKEND_NAME = 'dummy'


class DummySearchResult(SearchResult):
    dm = type('DummyModel', (object,), {})
    
    def _get_object(self):
        return self.dm()
    
    def _set_object(self, obj):
        pass
    
    def _get_model(self):
        return self.dm
    
    def _set_model(self, obj):
        pass

    def content_type(self):
        return u"%s.%s" % (self.app_label, self.model_name)


class SearchBackend(BaseSearchBackend):
    def update(self, indexer, iterable):
        pass
    
    def remove(self, obj):
        pass
    
    def clear(self, models):
        pass
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=True, **kwargs):
        if query_string == '(content__exact hello AND content__exact world)':
            return {
                'results': [DummySearchResult('haystack', 'dummymodel', 1, 1.5)],
                'hits': 1,
            }
        
        return {
            'results': [],
            'hits': 0,
        }
    
    def prep_value(self, db_field, value):
        return value
    
    def more_like_this(self, model_instance, additional_query_string=None):
        return {
            'results': [],
            'hits': 0
        }


class SearchQuery(BaseSearchQuery):
    def __init__(self, backend=None):
        super(SearchQuery, self).__init__(backend=backend)
        self.backend = backend or SearchBackend()
    
    def build_query_fragment(self, field, filter_type, value):
        result = ''
        value = str(value)
        
        # Check to see if it's a phrase for an exact match.
        if ' ' in value:
            value = '"%s"' % value
        
        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        result = ' '.join([FILTER_SEPARATOR.join((field, filter_type)), value])
        return result
