# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models.loading import get_model

from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, log_query
from haystack.models import SearchResult
from haystack.routers import BaseRouter
from haystack.utils import get_identifier


class MockMasterSlaveRouter(BaseRouter):
    def for_read(self, **hints):
        return 'slave'

    def for_write(self, **hints):
        return 'master'


class MockPassthroughRouter(BaseRouter):
    def for_read(self, **hints):
        if hints.get('pass_through') is False:
            return 'pass'

        return None

    def for_write(self, **hints):
        if hints.get('pass_through') is False:
            return 'pass'

        return None


class MockSearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        super(MockSearchResult, self).__init__(app_label, model_name, pk, score, **kwargs)
        self._model = get_model('core', model_name)

MOCK_SEARCH_RESULTS = [MockSearchResult('core', 'MockModel', i, 1 - (i / 100.0)) for i in range(1, 100)]
MOCK_INDEX_DATA = {}

class MockSearchBackend(BaseSearchBackend):
    model_name = 'mockmodel'

    def update(self, index, iterable, commit=True):
        global MOCK_INDEX_DATA
        for obj in iterable:
            doc = index.full_prepare(obj)
            MOCK_INDEX_DATA[doc['id']] = doc

    def remove(self, obj, commit=True):
        global MOCK_INDEX_DATA
        if commit == True:
            del(MOCK_INDEX_DATA[get_identifier(obj)])

    def clear(self, models=None, commit=True):
        global MOCK_INDEX_DATA
        MOCK_INDEX_DATA = {}

    @log_query
    def search(self, query_string, **kwargs):
        from haystack import connections
        global MOCK_INDEX_DATA
        results = []
        hits = len(MOCK_INDEX_DATA)
        indexed_models = connections['default'].get_unified_index().get_indexed_models()

        def junk_sort(key):
            app, model, pk = key.split('.')

            if pk.isdigit():
                return int(pk)
            else:
                return ord(pk[0])

        sliced = sorted(MOCK_INDEX_DATA, key=junk_sort)

        for i, result in enumerate(sliced):
            app_label, model_name, pk = result.split('.')
            model = get_model(app_label, model_name)

            if model:
                if model in indexed_models:
                    results.append(MockSearchResult(app_label, model_name, pk, 1 - (i / 100.0)))
                else:
                    hits -= 1
            else:
                hits -= 1

        return {
            'results': results[kwargs.get('start_offset'):kwargs.get('end_offset')],
            'hits': hits,
        }

    def more_like_this(self, model_instance, additional_query_string=None, result_class=None):
        return self.search(query_string='*')


class CharPKMockSearchBackend(MockSearchBackend):
    model_name = 'charpkmockmodel'
    mock_search_results = [MockSearchResult('core', 'CharPKMockModel', 'sometext', 0.5),
                           MockSearchResult('core', 'CharPKMockModel', '1234', 0.3)]

class ReadQuerySetMockSearchBackend(MockSearchBackend):
    model_name = 'afifthmockmodel'
    mock_search_results = [MockSearchResult('core', 'afifthmockmodel', 1, 2),
                           MockSearchResult('core', 'afifthmockmodel', 2, 2)]

class MixedMockSearchBackend(MockSearchBackend):
    @log_query
    def search(self, query_string, **kwargs):
        if kwargs.get('end_offset') and kwargs['end_offset'] > 30:
            kwargs['end_offset'] = 30

        result_info = super(MixedMockSearchBackend, self).search(query_string, **kwargs)
        result_info['hits'] = 30

        # Remove search results from other models.
        temp_results = []

        for result in result_info['results']:
            if not int(result.pk) in (9, 13, 14):
                # MockSearchResult('core', 'AnotherMockModel', 9, .1)
                # MockSearchResult('core', 'AnotherMockModel', 13, .1)
                # MockSearchResult('core', 'NonexistentMockModel', 14, .1)
                temp_results.append(result)

        result_info['results'] = temp_results

        return result_info


class MockSearchQuery(BaseSearchQuery):
    def build_query(self):
        return ''

    def clean(self, query_fragment):
        return query_fragment

    # def run_mlt(self):
    #     # To simulate the chunking behavior of a regular search, return a slice
    #     # of our results using start/end offset.
    #     final_query = self.build_query()
    #     results = self.backend.more_like_this(self._mlt_instance, final_query)
    #     import pdb; pdb.set_trace()
    #     self._results = results['results'][self.start_offset:self.end_offset]
    #     self._hit_count = results['hits']


class MockEngine(BaseEngine):
    backend = MockSearchBackend
    query = MockSearchQuery
