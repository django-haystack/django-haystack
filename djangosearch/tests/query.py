from django.test import TestCase
from djangosearch.backends import QueryFilter, BaseSearchQuery
from djangosearch.backends.dummy import SearchBackend as DummySearchBackend
from djangosearch.backends.dummy import SearchQuery as DummySearchQuery
from djangosearch.models import SearchResult
from djangosearch.query import SearchQuerySet
from djangosearch.sites import SearchIndex
from djangosearch.tests.mocks import MockModel, MockSearchQuery, MockSearchBackend, MOCK_SEARCH_RESULTS


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
        self.bsq = BaseSearchQuery(backend=DummySearchBackend())
    
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
    
    def test_set_limits(self):
        self.assertEqual(self.bsq.start_offset, 0)
        self.assertEqual(self.bsq.end_offset, None)
        
        self.bsq.set_limits(10, 50)
        self.assertEqual(self.bsq.start_offset, 10)
        self.assertEqual(self.bsq.end_offset, 50)
    
    def test_clear_limits(self):
        self.bsq.set_limits(10, 50)
        self.assertEqual(self.bsq.start_offset, 10)
        self.assertEqual(self.bsq.end_offset, 50)
        
        self.bsq.clear_limits()
        self.assertEqual(self.bsq.start_offset, 0)
        self.assertEqual(self.bsq.end_offset, None)
    
    def test_add_boost(self):
        self.assertEqual(self.bsq.boost, {})
        
        self.bsq.add_boost('foo', 10)
        self.assertEqual(self.bsq.boost, {'foo': 10})
    
    def test_more_like_this(self):
        mock = MockModel()
        mock.id = 1
        msq = MockSearchQuery(backend=MockSearchBackend())
        msq.more_like_this(mock)
        
        self.assertEqual(msq.get_count(), 100)
        self.assertEqual(msq.get_results()[0], MOCK_SEARCH_RESULTS[0])
    
    def test_run(self):
        msq = MockSearchQuery(backend=MockSearchBackend())
        self.assertEqual(len(msq.get_results()), 100)
        self.assertEqual(msq.get_results()[0], MOCK_SEARCH_RESULTS[0])
    
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


class SearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(SearchQuerySetTestCase, self).setUp()
        self.bsqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()))
        self.msqs = SearchQuerySet(query=MockSearchQuery(backend=MockSearchBackend()))
    
    def test_len(self):
        # Dummy always returns 0.
        self.assertEqual(len(self.bsqs), 0)
        
        self.assertEqual(len(self.msqs), 100)
    
    def test_iter(self):
        # Dummy always returns [].
        self.assertEqual([result for result in self.bsqs.all()], [])
        
        msqs = self.msqs.all()
        results = [result for result in msqs]
        self.assertEqual(results, MOCK_SEARCH_RESULTS)
    
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
        self.assert_(isinstance(sqs, SearchQuerySet))
    
    def test_filter(self):
        sqs = self.bsqs.filter(content='foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
    
    def test_exclude(self):
        sqs = self.bsqs.exclude(content='foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
    
    def test_order_by(self):
        sqs = self.bsqs.order_by('foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assert_('foo' in sqs.query.order_by)
    
    def test_models(self):
        mock_index_site = SearchIndex()
        mock_index_site.register(MockModel)
        
        bsqs = SearchQuerySet(site=mock_index_site)
        sqs = bsqs.models(MockModel)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.models), 1)
    
    def test_boost(self):
        sqs = self.bsqs.boost(foo=10)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.boost.keys()), 1)
    
    def test_raw_search(self):
        self.assertEqual(len(self.bsqs.raw_search('foo')), 0)
        self.assertEqual(len(self.bsqs.raw_search('content__exact hello OR content__exact world')), 1)
    
    def test_load_all(self):
        sqs = self.msqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(sqs[0].object.foo, 'bar')
    
    def test_auto_query(self):
        sqs = self.bsqs.auto_query('test search -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: OR content__exact=test>', '<QueryFilter: OR content__exact=search>', '<QueryFilter: NOT content__exact=stuff>'])
    
    def test_count(self):
        self.assertEqual(self.bsqs.count(), 0)
    
    def test_best_match(self):
        self.assert_(isinstance(self.msqs.best_match(), SearchResult))
    
    def test_latest(self):
        self.assert_(isinstance(self.msqs.latest('pub_date'), SearchResult))
    
    def test_more_like_this(self):
        mock = MockModel()
        mock.id = 1
        
        self.assertEqual(len(self.msqs.more_like_this(mock)), 100)
    
    def test_clone(self):
        results = self.msqs.filter(foo='bar', foo__lt='10')
        
        clone = results._clone()
        self.assert_(isinstance(clone, SearchQuerySet))
        self.assertEqual(clone.site, results.site)
        self.assertEqual(str(clone.query), str(results.query))
        self.assertEqual(clone._result_cache, [])
        self.assertEqual(clone._result_count, None)
        self.assertEqual(clone._cache_full, False)
