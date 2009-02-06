from django.conf import settings
from django.test import TestCase
from djangosearch.backends.solr import SearchBackend
from djangosearch.sites import IndexSite


class SolrIndexSite(IndexSite):
    pass


class SolrSearchBackendTestCase(TestCase):
    def setUp(self):
        super(SolrSearchBackendTestCase, self).setUp()
        
        # Stow.
        self.old_solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:9000/solr/test_default')
        settings.SOLR_URL = 'http://localhost:9000/solr/test_default'
        
        self.sb = SearchBackend()
    
    def tearDown(self):
        settings.SOLR_URL = self.old_solr_url
        super(SolrSearchBackendTestCase, self).tearDown()
    
    def test_update(self):
        self.fail()
    
    def test_remove(self):
        self.fail()
    
    def test_clear(self):
        self.fail()
    
    def test_search(self):
        self.fail()
