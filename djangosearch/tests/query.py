from django.db import models
from django.test import TestCase
from djangosearch.backends.base import BaseSearchQuery
from djangosearch.query import BaseSearchQuerySet


class MockModel(models.Model):
    pass


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
        pass
    
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


class SearchQuerySetTestCase(TestCase):
    pass
