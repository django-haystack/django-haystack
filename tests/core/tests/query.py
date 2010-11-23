# -*- coding: utf-8 -*-
import datetime
from django.conf import settings
from django.test import TestCase
import haystack
from haystack import backends
from haystack.backends import SQ, BaseSearchQuery
from haystack.backends.dummy_backend import SearchBackend as DummySearchBackend
from haystack.backends.dummy_backend import SearchQuery as DummySearchQuery
from haystack.exceptions import HaystackError, FacetingError, NotRegistered
from haystack.models import SearchResult
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel, CharPKMockModel
from core.tests.mocks import MockSearchQuery, MockSearchBackend, CharPKMockSearchBackend, MixedMockSearchBackend, MOCK_SEARCH_RESULTS
try:
    set
except NameError:
    from sets import Set as set

test_pickling = True

try:
    import cPickle as pickle
except ImportError:
    try:
        import pickle
    except ImportError:
        test_pickling = False


class SQTestCase(TestCase):
    def test_split_expression(self):
        sq = SQ(foo='bar')
        
        self.assertEqual(sq.split_expression('foo'), ('foo', 'exact'))
        self.assertEqual(sq.split_expression('foo__exact'), ('foo', 'exact'))
        self.assertEqual(sq.split_expression('foo__lt'), ('foo', 'lt'))
        self.assertEqual(sq.split_expression('foo__lte'), ('foo', 'lte'))
        self.assertEqual(sq.split_expression('foo__gt'), ('foo', 'gt'))
        self.assertEqual(sq.split_expression('foo__gte'), ('foo', 'gte'))
        self.assertEqual(sq.split_expression('foo__in'), ('foo', 'in'))
        self.assertEqual(sq.split_expression('foo__startswith'), ('foo', 'startswith'))
        self.assertEqual(sq.split_expression('foo__range'), ('foo', 'range'))
        
        # Unrecognized filter. Fall back to exact.
        self.assertEqual(sq.split_expression('foo__moof'), ('foo', 'exact'))
    
    def test_repr(self):
        self.assertEqual(repr(SQ(foo='bar')), '<SQ: AND foo__exact=bar>')
        self.assertEqual(repr(SQ(foo=1)), '<SQ: AND foo__exact=1>')
        self.assertEqual(repr(SQ(foo=datetime.datetime(2009, 5, 12, 23, 17))), '<SQ: AND foo__exact=2009-05-12 23:17:00>')
    
    def test_simple_nesting(self):
        sq1 = SQ(foo='bar')
        sq2 = SQ(foo='bar')
        bigger_sq = SQ(sq1 & sq2)
        self.assertEqual(repr(bigger_sq), '<SQ: AND (foo__exact=bar AND foo__exact=bar)>')
        
        another_bigger_sq = SQ(sq1 | sq2)
        self.assertEqual(repr(another_bigger_sq), '<SQ: AND (foo__exact=bar OR foo__exact=bar)>')
        
        one_more_bigger_sq = SQ(sq1 & ~sq2)
        self.assertEqual(repr(one_more_bigger_sq), '<SQ: AND (foo__exact=bar AND NOT (foo__exact=bar))>')
        
        mega_sq = SQ(bigger_sq & SQ(another_bigger_sq | ~one_more_bigger_sq))
        self.assertEqual(repr(mega_sq), '<SQ: AND ((foo__exact=bar AND foo__exact=bar) AND ((foo__exact=bar OR foo__exact=bar) OR NOT ((foo__exact=bar AND NOT (foo__exact=bar)))))>')


class BaseSearchQueryTestCase(TestCase):
    def setUp(self):
        super(BaseSearchQueryTestCase, self).setUp()
        self.bsq = BaseSearchQuery(backend=DummySearchBackend())
    
    def test_get_count(self):
        self.bsq.add_filter(SQ(foo='bar'))
        self.assertRaises(NotImplementedError, self.bsq.get_count)
    
    def test_build_query(self):
        self.bsq.add_filter(SQ(foo='bar'))
        self.assertRaises(NotImplementedError, self.bsq.build_query)
    
    def test_add_filter(self):
        self.assertEqual(len(self.bsq.query_filter), 0)
        
        self.bsq.add_filter(SQ(foo='bar'))
        self.assertEqual(len(self.bsq.query_filter), 1)
        
        self.bsq.add_filter(SQ(foo__lt='10'))
        
        self.bsq.add_filter(~SQ(claris='moof'))
        
        self.bsq.add_filter(SQ(claris='moof'), use_or=True)
        
        self.assertEqual(repr(self.bsq.query_filter), '<SQ: OR ((foo__exact=bar AND foo__lt=10 AND NOT (claris__exact=moof)) OR claris__exact=moof)>')
        
        self.bsq.add_filter(SQ(claris='moof'))

        self.assertEqual(repr(self.bsq.query_filter), '<SQ: AND (((foo__exact=bar AND foo__lt=10 AND NOT (claris__exact=moof)) OR claris__exact=moof) AND claris__exact=moof)>')
    
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
        self.assertEqual(self.bsq.query_facets, [('foo', 'bar')])
        
        self.bsq.add_query_facet('moof', 'baz')
        self.assertEqual(self.bsq.query_facets, [('foo', 'bar'), ('moof', 'baz')])
        
        self.bsq.add_query_facet('foo', 'baz')
        self.assertEqual(self.bsq.query_facets, [('foo', 'bar'), ('moof', 'baz'), ('foo', 'baz')])
    
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
        self.bsq.add_filter(SQ(foo='bar'))
        self.bsq.add_filter(SQ(foo__lt='10'))
        self.bsq.add_filter(~SQ(claris='moof'))
        self.bsq.add_filter(SQ(claris='moof'), use_or=True)
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
        self.assertEqual(len(clone.query_filter), 2)
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
    
    def test_log_query(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        
        # Stow.
        old_site = haystack.site
        old_debug = settings.DEBUG
        test_site = SearchSite()
        test_site.register(MockModel)
        haystack.site = test_site
        settings.DEBUG = False
        
        msq = MockSearchQuery(backend=MockSearchBackend())
        self.assertEqual(len(msq.get_results()), 100)
        self.assertEqual(len(backends.queries), 0)
        
        settings.DEBUG = True
        # Redefine it to clear out the cached results.
        msq2 = MockSearchQuery(backend=MockSearchBackend())
        self.assertEqual(len(msq2.get_results()), 100)
        self.assertEqual(len(backends.queries), 1)
        self.assertEqual(backends.queries[0]['query_string'], '')
        
        msq3 = MockSearchQuery(backend=MockSearchBackend())
        msq3.add_filter(SQ(foo='bar'))
        len(msq3.get_results())
        self.assertEqual(len(backends.queries), 2)
        self.assertEqual(backends.queries[0]['query_string'], '')
        self.assertEqual(backends.queries[1]['query_string'], '')
        
        # Restore.
        haystack.site = old_site
        settings.DEBUG = old_debug
    
    def test_regression_site_kwarg(self):
        # Stow.
        test_site = SearchSite()
        test_site.register(MockModel)
        
        msq = MockSearchQuery(site=test_site)
        self.assertEqual(msq.backend.site.get_indexed_models(), [MockModel])
    
    def test_regression_dummy_unicode(self):
        dsq = DummySearchQuery(backend=DummySearchBackend())
        self.assertEqual(dsq.build_query_fragment('foo', 'exact', 'bar'), 'foo__exact bar')
        self.assertEqual(dsq.build_query_fragment('foo', 'exact', u'☃'), u'foo__exact ☃')


class SearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(SearchQuerySetTestCase, self).setUp()
        self.bsqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()))
        self.msqs = SearchQuerySet(query=MockSearchQuery(backend=MockSearchBackend()))
        self.mmsqs = SearchQuerySet(query=MockSearchQuery(backend=MixedMockSearchBackend()))
        
        # Stow.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel)
        test_site.register(CharPKMockModel)
        haystack.site = test_site
        
        backends.reset_search_queries()
    
    def tearDown(self):
        # Restore.
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        super(SearchQuerySetTestCase, self).tearDown()
    
    def test_len(self):
        # Dummy always returns 0.
        self.assertEqual(len(self.bsqs), 0)
        
        self.assertEqual(len(self.msqs), 100)
    
    def test_repr(self):
        self.assertEqual(repr(self.bsqs), '[]')
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(repr(self.msqs), "[<SearchResult: core.MockModel (pk=0)>, <SearchResult: core.MockModel (pk=1)>, <SearchResult: core.MockModel (pk=2)>, <SearchResult: core.MockModel (pk=3)>, <SearchResult: core.MockModel (pk=4)>, <SearchResult: core.MockModel (pk=5)>, <SearchResult: core.MockModel (pk=6)>, <SearchResult: core.MockModel (pk=7)>, <SearchResult: core.MockModel (pk=8)>, <SearchResult: core.MockModel (pk=9)>, <SearchResult: core.MockModel (pk=10)>, <SearchResult: core.MockModel (pk=11)>, <SearchResult: core.MockModel (pk=12)>, <SearchResult: core.MockModel (pk=13)>, <SearchResult: core.MockModel (pk=14)>, <SearchResult: core.MockModel (pk=15)>, <SearchResult: core.MockModel (pk=16)>, <SearchResult: core.MockModel (pk=17)>, <SearchResult: core.MockModel (pk=18)>, '...(remaining elements truncated)...']")
        self.assertEqual(len(backends.queries), 1)
    
    def test_iter(self):
        # Dummy always returns [].
        self.assertEqual([result for result in self.bsqs.all()], [])
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        msqs = self.msqs.all()
        results = [result for result in msqs]
        self.assertEqual(results, MOCK_SEARCH_RESULTS)
        self.assertEqual(len(backends.queries), 10)
    
    def test_slice(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.msqs.all()
        self.assertEqual(results[1:11], MOCK_SEARCH_RESULTS[1:11])
        self.assertEqual(len(backends.queries), 1)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.msqs.all()
        self.assertEqual(results[50], MOCK_SEARCH_RESULTS[50])
        self.assertEqual(len(backends.queries), 1)
    
    def test_manual_iter(self):
        results = self.msqs.all()
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        
        for offset, result in enumerate(results._manual_iter()):
            self.assertEqual(result, MOCK_SEARCH_RESULTS[offset])
        
        self.assertEqual(len(backends.queries), 10)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        # Test to ensure we properly fill the cache, even if we get fewer
        # results back (not in the SearchSite) than the hit count indicates.
        # This will hang indefinitely if broken.
        results = self.mmsqs.all()
        loaded = [result.pk for result in results._manual_iter()]
        self.assertEqual(loaded, [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29])
        self.assertEqual(len(backends.queries), 8)
    
    def test_fill_cache(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.msqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(backends.queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(backends.queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(backends.queries), 2)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        # Test to ensure we properly fill the cache, even if we get fewer
        # results back (not in the SearchSite) than the hit count indicates.
        results = self.mmsqs.all()
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 0)
        self.assertEqual([result.pk for result in results._result_cache if result is not None], [])
        self.assertEqual(len(backends.queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 9)
        self.assertEqual([result.pk for result in results._result_cache if result is not None], [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(len(backends.queries), 2)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 17)
        self.assertEqual([result.pk for result in results._result_cache if result is not None], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18, 19])
        self.assertEqual(len(backends.queries), 4)
        results._fill_cache(20, 30)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 27)
        self.assertEqual([result.pk for result in results._result_cache if result is not None], [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29])
        self.assertEqual(len(backends.queries), 6)
    
    def test_cache_is_full(self):
        # Dummy always has a count of 0 and an empty _result_cache, hence True.
        self.assertEqual(self.bsqs._cache_is_full(), False)
        results = self.bsqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(self.msqs._cache_is_full(), False)
        results = self.msqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(backends.queries), 10)
    
    def test_all(self):
        sqs = self.bsqs.all()
        self.assert_(isinstance(sqs, SearchQuerySet))
    
    def test_filter(self):
        sqs = self.bsqs.filter(content='foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 1)
    
    def test_exclude(self):
        sqs = self.bsqs.exclude(content='foo')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 1)
    
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
        
        # This will produce a warning.
        mock_index_site.unregister(AnotherMockModel)
        sqs = bsqs.models(AnotherMockModel)
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.models), 1)
    
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
        self.assertEqual(sqs.spelling_suggestion('indexy'), None)
    
    def test_raw_search(self):
        self.assertEqual(len(self.bsqs.raw_search('foo')), 0)
        self.assertEqual(len(self.bsqs.raw_search('(content__exact hello AND content__exact world)')), 1)
    
    def test_load_all(self):
        # Models with character primary keys
        sqs = SearchQuerySet(query=MockSearchQuery(backend=CharPKMockSearchBackend()))
        results = sqs.load_all().all()
        self.assertEqual(len(results._result_cache), 0)
        results._fill_cache(0, 2)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 2)
        
        # If nothing is registered, you get nothing.
        haystack.site.unregister(MockModel)
        haystack.site.unregister(CharPKMockModel)
        sqs = self.msqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs), 0)
        
        # For full tests, see the solr_backend.
    
    def test_auto_query(self):
        sqs = self.bsqs.auto_query('test search -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND (content__exact=test AND content__exact=search AND NOT (content__exact=stuff))>')
        
        sqs = self.bsqs.auto_query('test "my thing" search -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND (content__exact=my thing AND content__exact=test AND content__exact=search AND NOT (content__exact=stuff))>')
        
        sqs = self.bsqs.auto_query('test "my thing" search \'moar quotes\' -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), "<SQ: AND (content__exact=my thing AND content__exact=test AND content__exact=search AND content__exact='moar AND content__exact=quotes' AND NOT (content__exact=stuff))>")
        
        sqs = self.bsqs.auto_query('test "my thing" search \'moar quotes\' "foo -stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND (content__exact=my thing AND content__exact=test AND content__exact=search AND content__exact=\'moar AND content__exact=quotes\' AND content__exact="foo AND NOT (content__exact=stuff))>')
        
        sqs = self.bsqs.auto_query('test - stuff')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND (content__exact=test AND content__exact=- AND content__exact=stuff)>')
        
        # Ensure bits in exact matches get escaped properly as well.
        sqs = self.bsqs.auto_query('"pants:rule"')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND content__exact=pants:rule>')
    
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
        try:
            sqs = self.bsqs.date_facet('foo', start_date=datetime.date(2008, 2, 25), end_date=datetime.date(2009, 2, 25), gap_by='smarblaph')
            self.fail()
        except FacetingError, e:
            self.assertEqual(str(e), "The gap_by ('smarblaph') must be one of the following: year, month, day, hour, minute, second.")
        
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
        
        # Test multiple query facets on a single field
        sqs3 = self.bsqs.query_facet('foo', '[bar TO *]').query_facet('bar', '[100 TO 499]').query_facet('foo', '[1000 TO 1499]')
        self.assert_(isinstance(sqs3, SearchQuerySet))
        self.assertEqual(len(sqs3.query.query_facets), 3)
    
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
        self.assertEqual(len(sqs.query.query_filter), 1)
        
        # A second instance should inherit none of the changes from above.
        sqs = self.bsqs.filter(content='bar')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 1)
    
    def test_none(self):
        sqs = self.bsqs.none()
        self.assert_(isinstance(sqs, EmptySearchQuerySet))
        self.assertEqual(len(sqs), 0)
    
    def test___and__(self):
        sqs1 = self.bsqs.filter(content='foo')
        sqs2 = self.bsqs.filter(content='bar')
        sqs = sqs1 & sqs2
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
    
    def test___or__(self):
        sqs1 = self.bsqs.filter(content='foo')
        sqs2 = self.bsqs.filter(content='bar')
        sqs = sqs1 | sqs2
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
    
    def test_regression_site_kwarg(self):
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        bsqs = SearchQuerySet(site=mock_index_site)
        self.assertEqual(set(bsqs.query.backend.site.get_indexed_models()), set([MockModel, AnotherMockModel]))


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
    
    def test_slice(self):
        sqs = self.esqs.filter(content='foo')
        self.assert_(isinstance(sqs, EmptySearchQuerySet))
        self.assertEqual(len(sqs), 0)
        self.assertEqual(sqs[:10], [])
        
        try:
            sqs[4]
            self.fail()
        except IndexError:
            pass
    
    def test_dictionary_lookup(self):
        """
        Ensure doing a dictionary lookup raises a TypeError so
        EmptySearchQuerySets can be used in templates.
        """
        self.assertRaises(TypeError, lambda: self.esqs['count'])


if test_pickling:
    class PickleSearchQuerySetTestCase(TestCase):
        def setUp(self):
            super(PickleSearchQuerySetTestCase, self).setUp()
            self.bsqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()))
            self.msqs = SearchQuerySet(query=MockSearchQuery(backend=MockSearchBackend()))
            self.mmsqs = SearchQuerySet(query=MockSearchQuery(backend=MixedMockSearchBackend()))
            
            # Stow.
            self.old_debug = settings.DEBUG
            settings.DEBUG = True
            self.old_site = haystack.site
            test_site = SearchSite()
            test_site.register(MockModel)
            test_site.register(CharPKMockModel)
            haystack.site = test_site
            
            backends.reset_search_queries()
        
        def tearDown(self):
            # Restore.
            haystack.site = self.old_site
            settings.DEBUG = self.old_debug
            super(PickleSearchQuerySetTestCase, self).tearDown()
        
        def test_pickling(self):
            results = self.msqs.all()
            
            for res in results:
                # Make sure the cache is full.
                pass
            
            in_a_pickle = pickle.dumps(results)
            like_a_cuke = pickle.loads(in_a_pickle)
            self.assertEqual(len(like_a_cuke), len(results))
            self.assertEqual(like_a_cuke[0].id, results[0].id)
