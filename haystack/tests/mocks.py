import datetime
from django.db import models
from django.utils.encoding import force_unicode
from haystack import indexes
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.models import SearchResult
from haystack.sites import SearchIndex


class MockDefaultManager(object):
    def all(self):
        results = []
        
        for pk in xrange(3):
            mock = MockModel()
            mock.id = pk
            mock.user = 'daniel%s' % pk
            mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
            results.append(mock)
        
        return results
    
    def in_bulk(self, pk_array):
        results = {}
        
        for pk in pk_array:
            mock = MockModel()
            mock.foo = 'bar'
            results[pk] = mock
        
        return results
    
    def get(self, pk):
        mock = MockModel()
        mock.id = pk
        mock.user = 'daniel%s' % pk
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        return mock
    

class MockOptions(object):
    def __init__(self, ct, verbose_name_plural):
        self.ct = ct
        self.verbose_name_plural = verbose_name_plural
        self.pk = type('pk', (object,), {'attname': 'id'})
        self.app_label, self.module_name = self.ct.split('.')
    
    def __str__(self):
        return self.ct


class MockModel(models.Model):
    _default_manager = MockDefaultManager()
    
    def __init__(self):
        self._meta = MockOptions('haystack.mockmodel', 'MockModels')


class AnotherMockModel(models.Model):
    _default_manager = MockDefaultManager()
    
    def __init__(self, verbose_name_plural):
        self._meta = MockOptions('haystack.anothermockmodel', 'AnotherMockModel')


class MockSearchIndex(SearchIndex):
    pass


class MockSearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        super(MockSearchResult, self).__init__(app_label, model_name, pk, score, **kwargs)
        self._model = MockModel


MOCK_SEARCH_RESULTS = [MockSearchResult('haystack', 'MockModel', i, 1 - (i / 100.0)) for i in xrange(100)]


class MockSearchBackend(BaseSearchBackend):
    def __init__(self):
        self.docs = {}
    
    def update(self, index, iterable, commit=True):
        for obj in iterable:
            doc = {}
            doc['id'] = self.get_identifier(obj)
            doc['django_ct_s'] = force_unicode("%s.%s" % (obj._meta.app_label, obj._meta.module_name))
            doc['django_id_s'] = force_unicode(obj.pk)
            
            for name, value in index.get_fields(obj):
                doc[name] = value
            
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


class MockTemplateField(indexes.TemplateField):
    def get_value(self, obj):
        return u"Indexed!\n%s" % obj.pk


class MockStoredTemplateField(indexes.TemplateField):
    def get_value(self, obj):
        return u"Stored!\n%s" % obj.pk


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
