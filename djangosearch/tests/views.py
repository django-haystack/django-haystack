from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import models
from django.test import TestCase
from djangosearch.backends.dummy import DummyModel
from djangosearch.forms import model_choices
from djangosearch.sites import IndexSite


class MockOptions(object):
    def __init__(self, ct, verbose_name_plural):
        self.ct = ct
        self.verbose_name_plural = verbose_name_plural
    
    def __str__(self):
        return self.ct


class MockModel(models.Model):
    def __init__(self):
        self._meta = MockOptions('djangosearch.mockmodel', 'MockModels')


class AnotherMockModel(models.Model):
    def __init__(self, verbose_name_plural):
        self._meta = MockOptions('djangosearch.anothermockmodel', 'AnotherMockModel')


class MockIndexSite(IndexSite):
    pass


class SearchViewTestCase(TestCase):
    urls = 'djangosearch.tests.urls'
    
    def setUp(self):
        super(SearchViewTestCase, self).setUp()
        
        # Stow.
        self.old_solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:9000/solr/default')
        settings.SOLR_URL = 'http://localhost:9000/solr/default'
    
    def tearDown(self):
        settings.SOLR_URL = self.old_solr_url
        super(SearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('djangosearch_search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_query(self):
        response = self.client.get(reverse('djangosearch_search'), {'query': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page'].object_list), 1)
        self.assertEqual(response.context['page'].object_list[0].model, DummyModel)
        self.assertEqual(response.context['page'].object_list[0].pk, 1)
    
    def test_model_choices(self):
        mis = MockIndexSite()
        mis.register(MockModel)
        mis.register(AnotherMockModel)
        self.assertEqual(len(model_choices(site=mis)), 2)
        self.assertEqual([option[1] for option in model_choices(site=mis)], [u'another mock models', u'mock models'])
