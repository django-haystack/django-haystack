"""
A fake backend for mocking during tests.
"""

from djangosearch.results import SearchResults
from djangosearch.query import RELEVANCE
from djangosearch.backends.base import SearchEngine as BaseSearchEngine

class SearchEngine(BaseSearchEngine):

    def update(self, indexer, iterable):
        pass

    def remove(self, obj):
        pass

    def clear(self, models):
        pass

    def search(self, q, models=None, order_by=RELEVANCE, limit=None, offset=None):
        return SearchResults(q, [], 0, lambda r: r)

    def prep_value(self, db_field, value):
        return value

