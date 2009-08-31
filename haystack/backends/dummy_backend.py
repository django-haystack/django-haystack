"""
A fake backend for dummying during tests.
"""
import datetime
from django.db import models
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.constants import FILTER_SEPARATOR
from haystack.models import SearchResult


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

    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None, **kwargs):
        if query_string == 'content__exact hello AND content__exact world':
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
    
    def build_query(self):
        filters = []
        
        for the_filter in self.query_filters:
            filter_list = []
            
            if the_filter.is_and():
                filter_list.append("AND")
            elif the_filter.is_not():
                filter_list.append("NOT")
            elif the_filter.is_or():
                filter_list.append("OR")
            
            filter_list.append(FILTER_SEPARATOR.join((the_filter.field, the_filter.filter_type)))
            filter_list.append(the_filter.value)
            
            if not len(filters):
                del(filter_list[0])
                
            filters.append(" ".join(filter_list))
        
        query = " ".join(filters)
        
        if self.order_by:
            query = "%s ORDER BY %s" % (query, ", ".join(self.order_by))
        
        return query
