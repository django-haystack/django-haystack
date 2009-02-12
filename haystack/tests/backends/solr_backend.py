import pysolr
from django.conf import settings
from django.test import TestCase
from haystack import indexes
from haystack.backends.solr import SearchBackend
from haystack import sites
from haystack.tests.mocks import MockModel, AnotherMockModel, MockContentField


class SolrMockModelIndex(indexes.ModelIndex):
    text = MockContentField()
    name = indexes.CharField('author')


class SolrSearchIndex(sites.SearchIndex):
    pass


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
        self.site = SolrSearchIndex()
        self.site.register(MockModel, SolrMockModelIndex)
        
        # Stow.
        self.old_site = sites.site
        sites.site = self.site
        
        self.sample_objs = []
        
        # Need to fix the app label, as this sometimes gets confused between
        # 'haystack' and 'tests'. Strange but true.
        MockModel._meta.app_label = 'haystack'
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock._meta.app_label = 'haystack'
            self.sample_objs.append(mock)
    
    def tearDown(self):
        settings.SOLR_URL = self.old_solr_url
        sites.site = self.old_site
        super(SolrSearchBackendTestCase, self).tearDown()
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Solr thinks is there.
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'text': 'Indexed!\n1', 'django_id_s': '1', 'django_ct_s': 'haystack.mockmodel', 'id': 'haystack.mockmodel.1', 'name': 'daniel1'}, {'text': 'Indexed!\n2', 'django_id_s': '2', 'django_ct_s': 'haystack.mockmodel', 'id': 'haystack.mockmodel.2', 'name': 'daniel2'}, {'text': 'Indexed!\n3', 'django_id_s': '3', 'django_ct_s': 'haystack.mockmodel', 'id': 'haystack.mockmodel.3', 'name': 'daniel3'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_solr.search('*:*').hits, 2)
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'text': 'Indexed!\n2', 'django_id_s': '2', 'django_ct_s': 'haystack.mockmodel', 'id': 'haystack.mockmodel.2', 'name': 'daniel2'}, {'text': 'Indexed!\n3', 'django_id_s': '3', 'django_ct_s': 'haystack.mockmodel', 'id': 'haystack.mockmodel.3', 'name': 'daniel3'}])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear()
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.assertEqual(self.sb.search(''), [])
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], ['1', '2', '3'])
        
        self.assertEqual(self.sb.search('', highlight=True), [])
        self.assertEqual(self.sb.search('Index', highlight=True)['hits'], 3)
        self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index', highlight=True)['results']], ['<em>Indexed</em>!\n1', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n3'])
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        # DRL_TODO: Even though I've confirmed MLT works correctly, it doesn't
        #           seem to find any similar documents. Need better sample data?
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
        self.assertEqual([result.pk for result in self.sb.more_like_this(self.sample_objs[0])['results']], [])
