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
        ands = " AND ".join(self.and_keywords)
        ors = " OR ".join(self.or_keywords)
        nots = " NOT ".join(self.not_keywords)
        order_by = " ".join(self.order_by)
        return "%s %s %s %s" % (ands, ors, nots, order_by)
    
    def clean(self, query_fragment):
        return query_fragment
