import pysolr
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from haystack import indexes
from haystack.sites import SearchSite
from core.models import MockModel


class SolrMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateField(model_attr='pub_date')


class ManagementCommandTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(ManagementCommandTestCase, self).setUp()
        self.solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL)
        
        self.site = SearchSite()
        self.site.register(MockModel, SolrMockSearchIndex)
        
        # Stow.
        import haystack
        self.old_site = haystack.site
        haystack.site = self.site
    
    def tearDown(self):
        import haystack
        haystack.site = self.old_site
        super(ManagementCommandTestCase, self).tearDown()
    
    def test_basic_commands(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)
        
        call_command('update_index', verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)
        
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)
        
        call_command('rebuild_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)
    
    def test_remove(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)
        
        call_command('update_index', verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)
        
        # Remove a model instance.
        MockModel.objects.get(pk=1).delete()
        self.assertEqual(self.solr.search('*:*').hits, 23)
        
        # Plain ``update_index`` doesn't fix it.
        call_command('update_index', verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)
        
        # With the remove flag, it's gone.
        call_command('update_index', remove=True, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 22)
    
    def test_multiprocessing(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)
        
        # Watch the output, make sure there are multiple pids.
        call_command('update_index', verbosity=2, workers=2, batchsize=5)
        self.assertEqual(self.solr.search('*:*').hits, 23)
