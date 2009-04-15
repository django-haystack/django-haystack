import datetime
from django.db import models
from django.utils.encoding import force_unicode
from haystack import indexes
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.models import SearchResult
from core.models import MockModel


class MockSearchResult(SearchResult):
    def __init__(self, app_label, module_name, pk, score, **kwargs):
        super(MockSearchResult, self).__init__(app_label, module_name, pk, score, **kwargs)
        self._model = MockModel


MOCK_SEARCH_RESULTS = [MockSearchResult('core', 'MockModel', i, 1 - (i / 100.0)) for i in xrange(100)]


class MockSearchBackend(BaseSearchBackend):
    def __init__(self):
        self.docs = {}
    
    def update(self, index, iterable, commit=True):
        for obj in iterable:
            doc = {}
            doc['id'] = self.get_identifier(obj)
            doc['django_ct_s'] = force_unicode("%s.%s" % (obj._meta.app_label, obj._meta.module_name))
            doc['django_id_s'] = force_unicode(obj.pk)
            doc.update(index.prepare(obj))
            self.docs[doc['id']] = doc

    def remove(self, obj, commit=True):
        del(self.docs[self.get_identifier(obj)])

    def clear(self, models=[], commit=True):
        self.docs = {}
    
    def search(self, query, highlight=False):
        return MOCK_SEARCH_RESULTS
    
    def more_like_this(self, model_instance):
        return {
            'results': MOCK_SEARCH_RESULTS,
            'hits': len(MOCK_SEARCH_RESULTS),
        }


class MockSearchQuery(BaseSearchQuery):
    def build_query(self):
        return ''
    
    def clean(self, query_fragment):
        return query_fragment
    
    def run(self):
        # To simulate the chunking behavior of a regular search, return a slice
        # of our results using start/end offset.
        final_query = self.build_query()
        self._results = self.backend.search(final_query)[self.start_offset:self.end_offset]
        self._hit_count = len(MOCK_SEARCH_RESULTS)
