"""
A fake backend for dummying during tests.
"""
from django.utils.encoding import force_unicode
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
    def update(self, indexer, iterable, commit=True):
        pass
    
    def remove(self, obj, commit=True):
        pass
    
    def clear(self, models=[], commit=True):
        pass
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
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
    
    def more_like_this(self, model_instance, additional_query_string=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=None, result_class=None, **kwargs):
        return {
            'results': [],
            'hits': 0
        }


class SearchQuery(BaseSearchQuery):
    def __init__(self, site=None, backend=None):
        super(SearchQuery, self).__init__(backend=backend)
        
        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)
    
    def build_query_fragment(self, field, filter_type, value):
        result = ''
        value = force_unicode(value)
        
        # Check to see if it's a phrase for an exact match.
        if ' ' in value:
            value = '"%s"' % value
        
        index_fieldname = self.backend.site.get_index_fieldname(field)
        
        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        result = ' '.join([FILTER_SEPARATOR.join((index_fieldname, filter_type)), value])
        return result
