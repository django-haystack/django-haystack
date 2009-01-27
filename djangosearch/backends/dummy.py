"""
A fake backend for mocking during tests.
"""
from djangosearch.backends.base import BaseSearchBackend, QueryFilter, BaseSearchQuery


class SearchBackend(BaseSearchBackend):
    def update(self, indexer, iterable):
        pass

    def remove(self, obj):
        pass

    def clear(self, models):
        pass

    def search(self, query):
        return []

    def prep_value(self, db_field, value):
        return value


class SearchQuery(BaseSearchQuery):
    def get_count(self):
        return 0
    
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
            
            filters.append(" ".join(filter_list))
            
        return "%s ORDER BY %s" % (" ".join(filters), ", ".join(self.order_by))
    
    def clean(self, query_fragment):
        return query_fragment
