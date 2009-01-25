from django.db import models
from django.test import TestCase
from djangosearch.backends.base import QueryFilter, BaseSearchQuery
from djangosearch.models import SearchResult
from djangosearch.query import BaseSearchQuerySet
from djangosearch.sites import IndexSite


class MockModel(models.Model):
    pass


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
        self.bsq = BaseSearchQuery()
    
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
    
    def test_clone(self):
        # DRL_FIXME: Make sure to test this well.
        pass


class BaseSearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(BaseSearchQuerySetTestCase, self).setUp()
        self.bsqs = BaseSearchQuerySet()
    
    def test_len(self):
        pass
    
    def test_iter(self):
        pass
    
    def test_slice(self):
        # DRL_FIXME: Will fail until the __getitem__ method works.
        pass
    
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
        # DRL_FIXME: Will fail until the __getitem__ method works.
        # self.assert_(isinstance(self.bsqs.best_match(), SearchResult))
        pass
    
    def test_latest(self):
        # DRL_FIXME: Will fail until the __getitem__ method works.
        # self.assert_(isinstance(self.bsqs.best_match(), SearchResult))
        pass
    
    def test_clone(self):
        # DRL_FIXME: Make sure to test this well.
        pass
