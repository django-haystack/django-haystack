from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from haystack.forms import model_choices
from haystack import sites
from core.models import MockModel, AnotherMockModel


class SearchViewTestCase(TestCase):
    def setUp(self):
        super(SearchViewTestCase, self).setUp()
        mock_index_site = sites.SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = sites.site
        sites.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        sites.site = self.old_site
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
