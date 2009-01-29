from django.core.urlresolvers import reverse
from django.test import TestCase


class SearchViewTestCase(TestCase):
    def test_search(self):
        response = self.client.get(reverse('djangosearch_search'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('djangosearch_search'), {'query': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['results']), 20)
