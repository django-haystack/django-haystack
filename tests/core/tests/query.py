import datetime
from django.test import TestCase
import haystack
from haystack.backends import QueryFilter, BaseSearchQuery
from haystack.backends.dummy_backend import SearchBackend as DummySearchBackend
from haystack.backends.dummy_backend import SearchQuery as DummySearchQuery
from haystack.models import SearchResult
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel
from core.tests.mocks import MockSearchQuery, MockSearchBackend, MixedMockSearchBackend, MOCK_SEARCH_RESULTS


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
        self.assertEqual(qf.split_expression('foo__startswith'), ('foo', 'startswith'))
        
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
    
    def test_repr(self):
        self.assertEqual(repr(QueryFilter('foo', 'bar')), '<QueryFilter: AND foo__exact=bar>')
        self.assertEqual(repr(QueryFilter('foo', 1)), '<QueryFilter: AND foo__exact=1>')
        self.assertEqual(repr(QueryFilter('foo', datetime.datetime(2009, 5, 12, 23, 17))), '<QueryFilter: AND foo__exact=2009-05-12 23:17:00>')


class BaseSearchQueryTestCase(TestCase):
    def setUp(self):
        super(BaseSearchQueryTestCase, self).setUp()
        self.bsq = BaseSearchQuery(backend=DummySearchBackend())
    
    def test_get_count(self):
        self.assertRaises(NotImplementedError, self.bsq.get_count)
    
    def test_build_query(self):
        self.assertRaises(NotImplementedError, self.bsq.build_query)
    
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
        
        self.bsq.add_model(AnotherMockModel)
        self.assertEqual(len(self.bsq.models), 2)
    
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
    
    def test_add_highlight(self):
        self.assertEqual(self.bsq.highlight, False)
        
        self.bsq.add_highlight()
        self.assertEqual(self.bsq.highlight, True)
    
    def test_more_like_this(self):
        mock = MockModel()
        mock.id = 1
        msq = MockSearchQuery(backend=MockSearchBackend())
        msq.more_like_this(mock)
        
        self.assertEqual(msq.get_count(), 100)
        self.assertEqual(msq.get_results()[0], MOCK_SEARCH_RESULTS[0])
    
    def test_add_field_facet(self):
        self.bsq.add_field_facet('foo')
        self.assertEqual(self.bsq.facets, set(['foo']))
        
        self.bsq.add_field_facet('bar')
        self.assertEqual(self.bsq.facets, set(['foo', 'bar']))
    
    def test_add_date_facet(self):
        self.bsq.add_date_facet('foo', start_date=datetime.date(2009, 2, 25), end_date=datetime.date(2009, 3, 25), gap_by='day')
        self.assertEqual(self.bsq.date_facets, {'foo': {'gap_by': 'day', 'start_date': datetime.date(2009, 2, 25), 'end_date': datetime.date(2009, 3, 25), 'gap_amount': 1}})
        
        self.bsq.add_date_facet('bar', start_date=datetime.date(2008, 1, 1), end_date=datetime.date(2009, 12, 1), gap_by='month')
        self.assertEqual(self.bsq.date_facets, {'foo': {'gap_by': 'day', 'start_date': datetime.date(2009, 2, 25), 'end_date': datetime.date(2009, 3, 25), 'gap_amount': 1}, 'bar': {'gap_by': 'month', 'start_date': datetime.date(2008, 1, 1), 'end_date': datetime.date(2009, 12, 1), 'gap_amount': 1}})
    
    def test_add_query_facet(self):
        self.bsq.add_query_facet('foo', 'bar')
        self.assertEqual(self.bsq.query_facets, {'foo': 'bar'})
        
        self.bsq.add_query_facet('moof', 'baz')
        self.assertEqual(self.bsq.query_facets, {'foo': 'bar', 'moof': 'baz'})
    
    def test_add_narrow_query(self):
        self.bsq.add_narrow_query('foo:bar')
        self.assertEqual(self.bsq.narrow_queries, set(['foo:bar']))
        
        self.bsq.add_narrow_query('moof:baz')
        self.assertEqual(self.bsq.narrow_queries, set(['foo:bar', 'moof:baz']))
    
    def test_run(self):
        # Stow.
        old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel)
        haystack.site = test_site
        
        msq = MockSearchQuery(backend=MockSearchBackend())
        self.assertEqual(len(msq.get_results()), 100)
        self.assertEqual(msq.get_results()[0], MOCK_SEARCH_RESULTS[0])
        
        # Restore.
        haystack.site = old_site
    
    def test_clone(self):
        self.bsq.add_filter('foo', 'bar')
        self.bsq.add_filter('foo__lt', '10')
        self.bsq.add_filter('claris', 'moof', use_not=True)
        self.bsq.add_filter('claris', 'moof', use_or=True)
        self.bsq.add_order_by('foo')
        self.bsq.add_model(MockModel)
        self.bsq.add_boost('foo', 2)
        self.bsq.add_highlight()
        self.bsq.add_field_facet('foo')
        self.bsq.add_date_facet('foo', start_date=datetime.date(2009, 1, 1), end_date=datetime.date(2009, 1, 31), gap_by='day')
        self.bsq.add_query_facet('foo', 'bar')
        self.bsq.add_narrow_query('foo:bar')
        
        clone = self.bsq._clone()
        self.assert_(isinstance(clone, BaseSearchQuery))
        self.assertEqual(len(clone.query_filters), 4)
        self.assertEqual(len(clone.order_by), 1)
        self.assertEqual(len(clone.models), 1)
        self.assertEqual(len(clone.boost), 1)
        self.assertEqual(clone.highlight, True)
        self.assertEqual(len(clone.facets), 1)
        self.assertEqual(len(clone.date_facets), 1)
        self.assertEqual(len(clone.query_facets), 1)
        self.assertEqual(len(clone.narrow_queries), 1)
        self.assertEqual(clone.start_offset, self.bsq.start_offset)
        self.assertEqual(clone.end_offset, self.bsq.end_offset)
        self.assertEqual(clone.backend, self.bsq.backend)


class SearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(SearchQuerySetTestCase, self).setUp()
        self.bsqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()))
        self.msqs = SearchQuerySet(query=MockSearchQuery(backend=MockSearchBackend()))
        self.mmsqs = SearchQuerySet(query=MockSearchQuery(backend=MixedMockSearchBackend()))
        
        # Stow.
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel)
        haystack.site = test_site
    
    def tearDown(self):
        # Restore.
        haystack.site = self.old_site
        super(SearchQuerySetTestCase, self).tearDown()
    
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
        
        # Test to ensure we properly fill the cache, even if we get fewer
        # results back (not in the SearchSite) than the hit count indicates.
        # This will hang indefinitely if broken.
        results = self.mmsqs.all()
        self.assertEqual([result.pk for result in results._manual_iter()], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29])
    
    def test_fill_cache(self):
        results = self.msqs.all()
        self.assertEqual(len(results._result_cache), 0)
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 10)
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 20)
        
        # Test to ensure we properly fill the cache, even if we get fewer
        # results back (not in the SearchSite) than the hit count indicates.
        results = self.mmsqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual([result.pk for result in results._result_cache], [])
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 10)
        self.assertEqual([result.pk for result in results._result_cache], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10])
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 20)
        self.assertEqual([result.pk for result in results._result_cache], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 17, 18, 19, 20, 21, 22])
        results._fill_cache()
        self.assertEqual(len(results._result_cache), 27)
        self.assertEqual([result.pk for result in results._result_cache], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29])
    
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
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        bsqs = SearchQuerySet(site=mock_index_site)
        
        sqs = bsqs.all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.models), 0)
        
        sqs = bsqs.models(MockModel)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.models), 1)
        
        sqs = bsqs.models(MockModel, AnotherMockModel)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.models), 2)
    
    def test_boost(self):
        sqs = self.bsqs.boost('foo', 10)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.boost.keys()), 1)
    
    def test_highlight(self):
        sqs = self.bsqs.highlight()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(sqs.query.highlight, True)
    
    def test_spelling(self):
        # Test the case where spelling support is disabled.
        sqs = self.bsqs.filter(content='Indx')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(sqs.spelling_suggestion(), None)
    
    def test_raw_search(self):
        self.assertEqual(len(self.bsqs.raw_search('foo')), 0)
        self.assertEqual(len(self.bsqs.raw_search('content__exact hello AND content__exact world')), 1)
    
    def test_load_all(self):
        # If nothing is registered, you get nothing.
        haystack.site.unregister(MockModel)
        sqs = self.msqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs), 0)
        
        # For full tests, see the solr_backend.
    
    def test_load_all_queryset(self):
        sqs = self.msqs.load_all()
        self.assertEqual(len(sqs._load_all_querysets), 0)
        
        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        
        # For full tests, see the solr_backend.
    
    def test_auto_query(self):
        sqs = self.bsqs.auto_query('test search -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=search>', '<QueryFilter: NOT content__exact=stuff>'])
        
        sqs = self.bsqs.auto_query('test "my thing" search -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=my thing>', '<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=search>', '<QueryFilter: NOT content__exact=stuff>'])
        
        sqs = self.bsqs.auto_query('test "my thing" search \'moar quotes\' -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=my thing>', '<QueryFilter: AND content__exact=moar quotes>', '<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=search>', '<QueryFilter: NOT content__exact=stuff>'])
        
        sqs = self.bsqs.auto_query('test "my thing" search \'moar quotes\' "foo -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=my thing>', '<QueryFilter: AND content__exact=moar quotes>', '<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=search>', '<QueryFilter: AND content__exact="foo>', '<QueryFilter: NOT content__exact=stuff>'])
        
        sqs = self.bsqs.auto_query('test - stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual([repr(the_filter) for the_filter in sqs.query.query_filters], ['<QueryFilter: AND content__exact=test>', '<QueryFilter: AND content__exact=->', '<QueryFilter: AND content__exact=stuff>'])
    
    def test_count(self):
        self.assertEqual(self.bsqs.count(), 0)
    
    def test_facet_counts(self):
        self.assertEqual(self.bsqs.facet_counts(), {})
    
    def test_best_match(self):
        self.assert_(isinstance(self.msqs.best_match(), SearchResult))
    
    def test_latest(self):
        self.assert_(isinstance(self.msqs.latest('pub_date'), SearchResult))
    
    def test_more_like_this(self):
        mock = MockModel()
        mock.id = 1
        
        self.assertEqual(len(self.msqs.more_like_this(mock)), 100)
    
    def test_facets(self):
        sqs = self.bsqs.facet('foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.facets), 1)
        
        sqs2 = self.bsqs.facet('foo').facet('bar')
        self.assert_(isinstance(sqs2, SearchQuerySet))
        self.assertEqual(len(sqs2.query.facets), 2)
    
    def test_date_facets(self):
        sqs = self.bsqs.date_facet('foo', start_date=datetime.date(2008, 2, 25), end_date=datetime.date(2009, 2, 25), gap_by='month')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.date_facets), 1)
        
        sqs2 = self.bsqs.date_facet('foo', start_date=datetime.date(2008, 2, 25), end_date=datetime.date(2009, 2, 25), gap_by='month').date_facet('bar', start_date=datetime.date(2007, 2, 25), end_date=datetime.date(2009, 2, 25), gap_by='year')
        self.assert_(isinstance(sqs2, SearchQuerySet))
        self.assertEqual(len(sqs2.query.date_facets), 2)
    
    def test_query_facets(self):
        sqs = self.bsqs.query_facet('foo', '[bar TO *]')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_facets), 1)
        
        sqs2 = self.bsqs.query_facet('foo', '[bar TO *]').query_facet('bar', '[100 TO 499]')
        self.assert_(isinstance(sqs2, SearchQuerySet))
        self.assertEqual(len(sqs2.query.query_facets), 2)
    
    def test_narrow(self):
        sqs = self.bsqs.narrow('foo:moof')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.narrow_queries), 1)
    
    def test_clone(self):
        results = self.msqs.filter(foo='bar', foo__lt='10')
        
        clone = results._clone()
        self.assert_(isinstance(clone, SearchQuerySet))
        self.assertEqual(clone.site, results.site)
        self.assertEqual(str(clone.query), str(results.query))
        self.assertEqual(clone._result_cache, [])
        self.assertEqual(clone._result_count, None)
        self.assertEqual(clone._cache_full, False)
    
    def test_chaining(self):
        sqs = self.bsqs.filter(content='foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
        
        # A second instance should inherit none of the changes from above.
        sqs = self.bsqs.filter(content='bar')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filters), 1)
    
    def test_none(self):
        sqs = self.bsqs.none()
        self.assert_(isinstance(sqs, EmptySearchQuerySet))
        self.assertEqual(len(sqs), 0)


class EmptySearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(EmptySearchQuerySetTestCase, self).setUp()
        self.esqs = EmptySearchQuerySet()
    
    def test_get_count(self):
        self.assertEqual(self.esqs.count(), 0)
        self.assertEqual(len(self.esqs.all()), 0)
    
    def test_filter(self):
        sqs = self.esqs.filter(content='foo')
        self.assert_(isinstance(sqs, EmptySearchQuerySet))
        self.assertEqual(len(sqs), 0)
    
    def test_exclude(self):
        sqs = self.esqs.exclude(content='foo')
        self.assert_(isinstance(sqs, EmptySearchQuerySet))
        self.assertEqual(len(sqs), 0)
