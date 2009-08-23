from django.db.models.loading import get_model
from django.utils.encoding import force_unicode
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.models import SearchResult
from core.models import MockModel


class MockSearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        super(MockSearchResult, self).__init__(app_label, model_name, pk, score, **kwargs)
        self._model = MockModel


MOCK_SEARCH_RESULTS = [MockSearchResult('core', 'MockModel', i, 1 - (i / 100.0)) for i in xrange(100)]


class MockSearchBackend(BaseSearchBackend):
    def __init__(self):
        self.docs = {}
    
    def update(self, index, iterable, commit=True):
        for obj in iterable:
            doc = {}
            doc['id'] = self.get_identifier(obj)
            doc['django_ct'] = force_unicode("%s.%s" % (obj._meta.app_label, obj._meta.module_name))
            doc['django_id'] = force_unicode(obj.pk)
            doc.update(index.prepare(obj))
            self.docs[doc['id']] = doc

    def remove(self, obj, commit=True):
        del(self.docs[self.get_identifier(obj)])

    def clear(self, models=[], commit=True):
        self.docs = {}
    
    def search(self, query, highlight=False):
        from haystack import site
        results = []
        hits = len(MOCK_SEARCH_RESULTS)
        indexed_models = site.get_indexed_models()
        
        for result in MOCK_SEARCH_RESULTS:
            model = get_model('core', 'mockmodel')
            
            if model:
                if model in indexed_models:
                    results.append(result)
                else:
                    hits -= 1
            else:
                hits -= 1
        
        return {
            'results': results,
            'hits': hits,
        }
    
    def more_like_this(self, model_instance, additional_query_string=None):
        return {
            'results': MOCK_SEARCH_RESULTS,
            'hits': len(MOCK_SEARCH_RESULTS),
        }


class MixedMockSearchBackend(MockSearchBackend):
    def search(self, query, highlight=False):
        result_info = super(MixedMockSearchBackend, self).search(query, highlight)
        result_info['results'] = result_info['results'][:30]
        result_info['hits'] = 30
        
        # Add search results from other models.
        del(result_info['results'][9]) # MockSearchResult('core', 'AnotherMockModel', 9, .1)
        del(result_info['results'][13]) # MockSearchResult('core', 'AnotherMockModel', 13, .1)
        del(result_info['results'][14]) # MockSearchResult('core', 'NonexistentMockModel', 14, .1)
        
        return result_info


class MockSearchQuery(BaseSearchQuery):
    def build_query(self):
        return ''
    
    def clean(self, query_fragment):
        return query_fragment
    
    def run(self):
        # To simulate the chunking behavior of a regular search, return a slice
        # of our results using start/end offset.
        final_query = self.build_query()
        results = self.backend.search(final_query)
        self._results = results['results'][self.start_offset:self.end_offset]
        self._hit_count = results['hits']
    
    def run_mlt(self):
        # To simulate the chunking behavior of a regular search, return a slice
        # of our results using start/end offset.
        final_query = self.build_query()
        results = self.backend.more_like_this(self._mlt_instance, final_query)
        self._results = results['results'][self.start_offset:self.end_offset]
        self._hit_count = results['hits']
