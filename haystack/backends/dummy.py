"""
A fake backend for dummying during tests.
"""
import datetime
from django.db import models
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.constants import FILTER_SEPARATOR
from haystack.models import SearchResult


class DummyDefaultManager(object):
    def all(self):
        results = []
        
        for pk in xrange(3):
            dummy = DummyModel()
            dummy.id = pk
            dummy.user = 'daniel%s' % pk
            dummy.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
            results.append(dummy)
        
        return results
    
    def in_bulk(self, pk_array):
        results = {}
        
        for pk in pk_array:
            dummy = DummyModel()
            dummy.foo = 'bar'
            results[pk] = dummy
        
        return results
    
    def get(self, pk):
        dummy = DummyModel()
        dummy.id = pk
        dummy.user = 'daniel%s' % pk
        dummy.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        return dummy


class DummyModel(models.Model):
    _default_manager = DummyDefaultManager()


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

    def search(self, query, highlight=False):
        if query == 'content__exact hello OR content__exact world':
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
    
    def more_like_this(self, model_instance):
        return {
            'results': [],
            'hits': 0
        }


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
