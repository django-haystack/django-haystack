from django.db.models.loading import get_model
from django.utils.encoding import force_unicode
from haystack.backends import BaseSearchBackend, BaseSearchQuery, log_query
from haystack.models import SearchResult
from haystack.utils import get_identifier
from core.models import MockModel


class MockSearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        super(MockSearchResult, self).__init__(app_label, model_name, pk, score, **kwargs)
        self._model = get_model('core', model_name)

MOCK_SEARCH_RESULTS = [MockSearchResult('core', 'MockModel', i, 1 - (i / 100.0)) for i in xrange(100)]


class MockSearchBackend(BaseSearchBackend):
    model_name = 'mockmodel'
    mock_search_results = MOCK_SEARCH_RESULTS
    
    def __init__(self, site=None):
        super(MockSearchBackend, self).__init__(site)
        self.docs = {}
    
    def update(self, index, iterable, commit=True):
        for obj in iterable:
            doc = index.full_prepare(obj)
            self.docs[doc['id']] = doc

    def remove(self, obj, commit=True):
        del(self.docs[get_identifier(obj)])

    def clear(self, models=[], commit=True):
        self.docs = {}
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, **kwargs):
        from haystack import site
        results = []
        hits = len(self.mock_search_results)
        indexed_models = site.get_indexed_models()
        
        sliced = self.mock_search_results
        
        for result in sliced:
            model = get_model('core', self.model_name)
            
            if model:
                if model in indexed_models:
                    results.append(result)
                else:
                    hits -= 1
            else:
                hits -= 1
        
        return {
            'results': results[start_offset:end_offset],
            'hits': hits,
        }
    
    def more_like_this(self, model_instance, additional_query_string=None):
        return {
            'results': self.mock_search_results,
            'hits': len(self.mock_search_results),
        }


class CharPKMockSearchBackend(MockSearchBackend):
    model_name = 'charpkmockmodel'
    mock_search_results = [MockSearchResult('core', 'CharPKMockModel', 'sometext', 0.5),
                           MockSearchResult('core', 'CharPKMockModel', '1234', 0.3)]

class MixedMockSearchBackend(MockSearchBackend):
    @log_query
    def search(self, query_string, **kwargs):
        if kwargs.get('end_offset') and kwargs['end_offset'] > 30:
            kwargs['end_offset'] = 30
        
        result_info = super(MixedMockSearchBackend, self).search(query_string, **kwargs)
        # result_info['results'] = result_info['results'][:30]
        result_info['hits'] = 30
        
        # Remove search results from other models.
        temp_results = []
        
        for result in result_info['results']:
            if not result.pk in (9, 13, 14):
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
    
    def run_mlt(self):
        # To simulate the chunking behavior of a regular search, return a slice
        # of our results using start/end offset.
        final_query = self.build_query()
        results = self.backend.more_like_this(self._mlt_instance, final_query)
        self._results = results['results'][self.start_offset:self.end_offset]
        self._hit_count = results['hits']


# For pickling tests.
SearchBackend = MockSearchBackend
SearchQuery = MockSearchQuery
