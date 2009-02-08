from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from djangosearch.backends.dummy import DummyModel
from djangosearch.forms import model_choices
from djangosearch.tests.mocks import MockSearchIndex, MockModel, AnotherMockModel


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
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['page'].object_list[0].model, DummyModel)
        self.assertEqual(response.context[-1]['page'].object_list[0].pk, 1)
    
    def test_model_choices(self):
        mis = MockSearchIndex()
        mis.register(MockModel)
        mis.register(AnotherMockModel)
        self.assertEqual(len(model_choices(site=mis)), 2)
        self.assertEqual([option[1] for option in model_choices(site=mis)], [u'another mock models', u'mock models'])
