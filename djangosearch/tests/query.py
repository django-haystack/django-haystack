from django.db import models
from django.test import TestCase
from djangosearch.backends import SearchBackend, QueryFilter, BaseSearchQuery
from djangosearch.backends.dummy import SearchBackend as DummySearchBackend
from djangosearch.backends.dummy import SearchQuery as DummySearchQuery
from djangosearch.models import SearchResult
from djangosearch.query import BaseSearchQuerySet
from djangosearch.sites import IndexSite


class MockModel(models.Model):
    pass


class MockSearchResult(SearchResult):
    def __init__(self, app_label, model_name, pk, score):
        self.model = MockModel
        self.pk = pk
        self.score = score
        self._object = None


MOCK_SEARCH_RESULTS = [MockSearchResult('djangosearch', 'MockModel', i, 1 - (i / 100.0)) for i in xrange(100)]


class MockSearchBackend(SearchBackend):
    """Simulates results coming out of the backend."""
    def search(self, query):
        return MOCK_SEARCH_RESULTS


class MockSearchQuery(BaseSearchQuery):
    def get_count(self):
        return len(self.run())
    
    def build_query(self):
        return ''
    
    def clean(self, query_fragment):
        return query_fragment
    
    def run(self):
        # To simulate the chunking behavior of a regular search, return a slice
        # of our results using start/end offset.
        final_query = self.build_query()
        return self.backend.search(final_query)[self.start_offset:self.end_offset]


class QueryFilterTestCase(TestCase):
    def test_not_and_or(self):
        self.assertRaises(AttributeError, QueryFilter, 'foo', 'bar', use_not=True, use_or=True)
    
    def test_split_expression(self):
        qf = QueryFilter('foo', 'bar')
        
        self.assertEqual(qf.split_expression('foo'), ('foo', 'exact'))
        self.assertEqual(qf.split_expression('foo__exact'), ('foo', 'exact'))
        self.assertEqual(qf.split_expression('foo__lt'), ('foo', 'lt'))
        self.assertEqual(qf.split_expression('foo__lte'), ('foo', 'lte'))
        self.assertEqual(qf.split_expression('foo__gt'), ('foo', 'gt'))
        self.assertEqual(qf.split_expression('foo__gte'), ('foo', 'gte'))
        self.assertEqual(qf.split_expression('foo__in'), ('foo', 'in'))
        
        self.assertEqual(qf.split_expression('foo__moof'), ('foo', 'exact'))
    
    def test_is_and(self):
        self.assertEqual(QueryFilter('foo', 'bar').is_and(), True)
        self.assertEqual(QueryFilter('foo', 'bar', use_not=True).is_and(), False)
        self.assertEqual(QueryFilter('foo', 'bar', use_or=True).is_and(), False)
    
    def test_is_not(self):
        self.assertEqual(QueryFilter('foo', 'bar').is_not(), False)
        self.assertEqual(QueryFilter('foo', 'bar', use_not=True).is_not(), True)
        self.assertEqual(QueryFilter('foo', 'bar', use_or=True).is_not(), False)
    
    def test_is_or(self):
        self.assertEqual(QueryFilter('foo', 'bar').is_or(), False)
        self.assertEqual(QueryFilter('foo', 'bar', use_not=True).is_or(), False)
        self.assertEqual(QueryFilter('foo', 'bar', use_or=True).is_or(), True)


class BaseSearchQueryTestCase(TestCase):
    def setUp(self):
        super(BaseSearchQueryTestCase, self).setUp()
        self.bsq = BaseSearchQuery(backend=DummySearchBackend)
    
    def test_get_count(self):
        self.assertRaises(NotImplementedError, self.bsq.get_count)
    
    def test_build_query(self):
        self.assertRaises(NotImplementedError, self.bsq.build_query)
    
    def test_clean(self):
        self.assertRaises(NotImplementedError, self.bsq.clean, 'foo')
    
    def test_add_filter(self):
        self.assertEqual(len(self.bsq.query_filters), 0)
        
        self.bsq.add_filter('foo', 'bar')
        self.assertEqual(len(self.bsq.query_filters), 1)
        
        self.bsq.add_filter('foo__lt', '10')
        self.assertEqual(len(self.bsq.query_filters), 2)
        
        self.bsq.add_filter('claris', 'moof', use_not=True)
        self.assertEqual(len(self.bsq.query_filters), 3)
        
        self.bsq.add_filter('claris', 'moof', use_or=True)
        self.assertEqual(len(self.bsq.query_filters), 4)
        
        self.assertEqual([repr(the_filter) for the_filter in self.bsq.query_filters], ['<QueryFilter: AND foo__exact=bar>', '<QueryFilter: AND foo__lt=10>', '<QueryFilter: NOT claris__exact=moof>', '<QueryFilter: OR claris__exact=moof>'])
    
    def test_add_order_by(self):
        self.assertEqual(len(self.bsq.order_by), 0)
        
        self.bsq.add_order_by('foo')
        self.assertEqual(len(self.bsq.order_by), 1)
    
    def test_clear_order_by(self):
        self.bsq.add_order_by('foo')
        self.assertEqual(len(self.bsq.order_by), 1)
        
        self.bsq.clear_order_by()
        self.assertEqual(len(self.bsq.order_by), 0)
    
    def test_add_model(self):
        self.assertEqual(len(self.bsq.models), 0)
        self.assertRaises(AttributeError, self.bsq.add_model, object)
        self.assertEqual(len(self.bsq.models), 0)
        
        self.bsq.add_model(MockModel)
        self.assertEqual(len(self.bsq.models), 1)
    
    def test_run(self):
        msq = MockSearchQuery(backend=MockSearchBackend)
        self.assertEqual(len(msq.run()), 100)
        self.assertEqual(msq.run()[0], MOCK_SEARCH_RESULTS[0])
    
    def test_clone(self):
        self.bsq.add_filter('foo', 'bar')
        self.bsq.add_filter('foo__lt', '10')
        self.bsq.add_filter('claris', 'moof', use_not=True)
        self.bsq.add_filter('claris', 'moof', use_or=True)
        self.bsq.add_order_by('foo')
        self.bsq.add_model(MockModel)
        
        clone = self.bsq._clone()
        self.assert_(isinstance(clone, BaseSearchQuery))
        self.assertEqual(len(clone.query_filters), 4)
        self.assertEqual(len(clone.order_by), 1)
        self.assertEqual(len(clone.models), 1)
        self.assertEqual(clone.start_offset, self.bsq.start_offset)
        self.assertEqual(clone.end_offset, self.bsq.end_offset)
        self.assertEqual(clone.backend, self.bsq.backend)


class BaseSearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(BaseSearchQuerySetTestCase, self).setUp()
        self.bsqs = BaseSearchQuerySet(query=DummySearchQuery())
        self.msqs = BaseSearchQuerySet(query=MockSearchQuery(backend=MockSearchBackend))
    
    def test_len(self):
        # Dummy always returns 0.
        self.assertEqual(len(self.bsqs), 0)
        
        self.assertEqual(len(self.msqs), 100)
    
    def test_iter(self):
        # Dummy always returns [].
        self.assertEqual([result for result in self.bsqs.all()], [])
        
        results = self.msqs.all()
        self.assertEqual([result for result in results], MOCK_SEARCH_RESULTS)
    
    def test_slice(self):
        self.assertEqual(self.msqs.all()[1:11], MOCK_SEARCH_RESULTS[1:11])
        self.assertEqual(self.msqs.all()[50], MOCK_SEARCH_RESULTS[50])
    
    def test_manual_iter(self):
        results = self.msqs.all()
        
        for offset, result in enumerate(results._manual_iter()):
            self.assertEqual(result, MOCK_SEARCH_RESULTS[offset])
    
    def test_fill_cache(self):
        results = self.msqs.all()
        self.assertEqual(len(results._result_cache), 0)
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 20)
    
    def test_cache_is_full(self):
        # Dummy always has a count of 0 and an empty _result_cache, hence True.
        self.assertEqual(self.bsqs._cache_is_full(), True)
        
        self.assertEqual(self.msqs._cache_is_full(), False)
        results = self.msqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
    
    def test_all(self):
        sqs = self.bsqs.all()
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
    
    def test_filter(self):
        sqs = self.bsqs.filter(content='foo')
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
    
    def test_exclude(self):
        sqs = self.bsqs.exclude(content='foo')
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
    
    def test_order_by(self):
        sqs = self.bsqs.order_by('foo')
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
        self.assert_('foo' in sqs.query.order_by)
    
    def test_models(self):
        mock_index_site = IndexSite()
        mock_index_site.register(MockModel)
        
        bsqs = BaseSearchQuerySet(site=mock_index_site)
        sqs = bsqs.models(MockModel)
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
        self.assertEqual(len(sqs.query.models), 1)
    
    def test_auto_query(self):
        sqs = self.bsqs.auto_query('test search -stuff')
        self.assert_(isinstance(sqs, BaseSearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=search>', '<QueryFilter: NOT content__exact=-stuff>'])
    
    def test_count(self):
        self.assertEqual(self.bsqs.count(), 0)
    
    def test_best_match(self):
        self.assert_(isinstance(self.msqs.best_match(), SearchResult))
    
    def test_latest(self):
        self.assert_(isinstance(self.msqs.latest('pub_date'), SearchResult))
    
    def test_clone(self):
        results = self.msqs.filter(foo='bar', foo__lt='10')
        
        clone = results._clone()
        self.assert_(isinstance(clone, BaseSearchQuerySet))
        self.assertEqual(clone.site, results.site)
        self.assertEqual(str(clone.query), str(results.query))
        self.assertEqual(clone._result_cache, [])
        self.assertEqual(clone._result_count, None)
        self.assertEqual(clone._cache_full, False)
