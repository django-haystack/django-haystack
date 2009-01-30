from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from djangosearch.backends.dummy import SearchBackend, SearchQuery
import djangosearch.query


class SearchViewTestCase(TestCase):
    def setUp(self):
        super(SearchViewTestCase, self).setUp()
        
        # Stow.
        self.old_solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:9000/solr/default')
        settings.SOLR_URL = 'http://localhost:9000/solr/default'
        
        sq = SearchQuery(backend=SearchBackend)
        sqs = djangosearch.query.BaseSearchQuerySet(query=sq)
        self.old_sqs = djangosearch.query.SearchQuerySet
        djangosearch.query.SearchQuerySet = sqs
    
    def tearDown(self):
        settings.SOLR_URL = self.old_solr_url
        djangosearch.query.SearchQuerySet = self.old_sqs
        super(SearchViewTestCase, self).tearDown()
    
    def test_search(self):
        response = self.client.get(reverse('djangosearch_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form'].get_models()), 1)
        
        response = self.client.get(reverse('djangosearch_search'), {'query': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page'].object_list), 1)
