from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
import haystack
from haystack.forms import model_choices, ModelSearchForm
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel


class SearchViewTestCase(TestCase):
    def setUp(self):
        super(SearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(SearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_query(self):
        response = self.client.get(reverse('haystack_search'), {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['page'].object_list[0].content_type(), 'haystack.dummymodel')
        self.assertEqual(response.context[-1]['page'].object_list[0].pk, 1)
    
    def test_invalid_page(self):
        response = self.client.get(reverse('haystack_search'), {'q': 'hello world', 'page': '165233'})
        self.assertEqual(response.status_code, 404)


class FacetedSearchViewTestCase(TestCase):
    def setUp(self):
        super(FacetedSearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(FacetedSearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_faceted_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['facets'], {})


class BasicSearchViewTestCase(TestCase):
    def setUp(self):
        super(BasicSearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(BasicSearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_basic_search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_query(self):
        response = self.client.get(reverse('haystack_basic_search'), {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(type(response.context[-1]['form']), ModelSearchForm)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['page'].object_list[0].content_type(), 'haystack.dummymodel')
        self.assertEqual(response.context[-1]['page'].object_list[0].pk, 1)
        self.assertEqual(response.context[-1]['query'], 'hello world')
    
    def test_invalid_page(self):
        response = self.client.get(reverse('haystack_basic_search'), {'q': 'hello world', 'page': '165233'})
        self.assertEqual(response.status_code, 404)
