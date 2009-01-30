"""
A fake backend for mocking during tests.
"""
from django.db import models
from djangosearch.backends import BaseSearchBackend, QueryFilter, BaseSearchQuery
from djangosearch.constants import FILTER_SEPARATOR
from djangosearch.models import SearchResult


class DummyModel(models.Model):
    pass


class DummySearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score):
        self.model = DummyModel
        self.pk = pk
        self.score = score
        self._object = None


class SearchBackend(BaseSearchBackend):
    def update(self, indexer, iterable):
        pass

    def remove(self, obj):
        pass

    def clear(self, models):
        pass

    def search(self, query):
        if query == 'content__exact hello AND content__exact world':
            return {
                'results': [DummySearchResult('djangosearch', 'mockmodel', 1, 1.5)],
                'hits': 1,
            }
        
        return {
            'results': [],
            'hits': 0,
        }

    def prep_value(self, db_field, value):
        return value


class SearchQuery(BaseSearchQuery):
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
    
    def clean(self, query_fragment):
        return query_fragment
