from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from haystack import backends
from core.models import MockModel
from solr_tests.tests.solr_backend import SolrMockModelSearchIndex, clear_solr_index


class SearchModelAdminTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(SearchModelAdminTestCase, self).setUp()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrMockModelSearchIndex)
        haystack.site = test_site
        
        # Wipe it clean.
        clear_solr_index()
        
        # Force indexing of the content.
        mockmodel_index = test_site.get_index(MockModel)
        mockmodel_index.update()
        
        superuser = User.objects.create_superuser(
            username='superuser',
            password='password',
            email='super@user.com',
        )
    
    def tearDown(self):
        # Restore.
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        super(SearchModelAdminTestCase, self).tearDown()
    
    def test_usage(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        
        self.assertEqual(self.client.login(username='superuser', password='password'), True)
        
        # First, non-search behavior.
        resp = self.client.get('/admin/core/mockmodel/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(resp.context['cl'].full_result_count, 23)
        
        # Then search behavior.
        resp = self.client.get('/admin/core/mockmodel/', data={'q': 'Haystack'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(backends.queries), 3)
        self.assertEqual(resp.context['cl'].full_result_count, 23)
        # Ensure they aren't search results.
        self.assertEqual(isinstance(resp.context['cl'].result_list[0], MockModel), True)
        self.assertEqual(resp.context['cl'].result_list[0].id, 17)
        
        # Make sure only changelist is affected.
        resp = self.client.get('/admin/core/mockmodel/1/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(backends.queries), 3)
        self.assertEqual(resp.context['original'].id, 1)
        