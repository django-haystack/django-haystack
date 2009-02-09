import httplib2
import pysolr
from django.conf import settings
from django.test import TestCase
from djangosearch import indexes
from djangosearch.backends.solr import SearchBackend
from djangosearch.sites import SearchIndex
from djangosearch.tests.mocks import MockModel, MockContentField


class SolrMockModelIndex(indexes.ModelIndex):
    text = MockContentField()
    name = indexes.CharField('author')


class SolrSearchBackendTestCase(TestCase):
    def setUp(self):
        super(SolrSearchBackendTestCase, self).setUp()
        
        # Stow.
        self.old_solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:9000/solr/test_default')
        settings.SOLR_URL = 'http://localhost:9000/solr/test_default'
        
        self.raw_solr = pysolr.Solr(settings.SOLR_URL)
        self.raw_solr.delete(q='*:*')
        
        self.sb = SearchBackend()
        self.smmi = SolrMockModelIndex(MockModel, backend=self.sb)
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            self.sample_objs.append(mock)
    
    def tearDown(self):
        settings.SOLR_URL = self.old_solr_url
        super(SolrSearchBackendTestCase, self).tearDown()
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Solr thinks is there.
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'text': 'Indexed!\n1', 'django_id_s': '1', 'django_ct_s': 'djangosearch.mockmodel', 'id': 'djangosearch.mockmodel.1', 'name': 'daniel1'}, {'text': 'Indexed!\n2', 'django_id_s': '2', 'django_ct_s': 'djangosearch.mockmodel', 'id': 'djangosearch.mockmodel.2', 'name': 'daniel2'}, {'text': 'Indexed!\n3', 'django_id_s': '3', 'django_ct_s': 'djangosearch.mockmodel', 'id': 'djangosearch.mockmodel.3', 'name': 'daniel3'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_solr.search('*:*').hits, 2)
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'text': 'Indexed!\n2', 'django_id_s': '2', 'django_ct_s': 'djangosearch.mockmodel', 'id': 'djangosearch.mockmodel.2', 'name': 'daniel2'}, {'text': 'Indexed!\n3', 'django_id_s': '3', 'django_ct_s': 'djangosearch.mockmodel', 'id': 'djangosearch.mockmodel.3', 'name': 'daniel3'}])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear()
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.assertEqual(self.sb.search(''), [])
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], ['1', '2', '3'])
