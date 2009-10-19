from django.test import TestCase
from haystack.models import SearchResult
from core.models import MockModel
from core.tests.mocks import MockSearchResult


class SearchResultTestCase(TestCase):
    def setUp(self):
        super(SearchResultTestCase, self).setUp()
        
        self.no_data = {}
        self.extra_data = {
            'stored': 'I am stored data. How fun.',
        }
        self.no_overwrite_data = {
            'django_id': 2,
            'django_ct': 'haystack.anothermockmodel',
            'stored': 'I am stored data. How fun.',
        }
        
        self.no_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 2)
        self.extra_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 3, **self.extra_data)
        self.no_overwrite_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 4, **self.no_overwrite_data)
    
    def test_init(self):
        self.assertEqual(self.no_data_sr.app_label, 'haystack')
        self.assertEqual(self.no_data_sr.model_name, 'mockmodel')
        self.assertEqual(self.no_data_sr.model, MockModel)
        self.assertEqual(self.no_data_sr.verbose_name, u'Mock model')
        self.assertEqual(self.no_data_sr.verbose_name_plural, u'Mock models')
        self.assertEqual(self.no_data_sr.pk, '1')
        self.assertEqual(self.no_data_sr.score, 2)
        self.assertEqual(self.no_data_sr.stored, None)
        
        self.assertEqual(self.extra_data_sr.app_label, 'haystack')
        self.assertEqual(self.extra_data_sr.model_name, 'mockmodel')
        self.assertEqual(self.extra_data_sr.model, MockModel)
        self.assertEqual(self.extra_data_sr.verbose_name, u'Mock model')
        self.assertEqual(self.extra_data_sr.verbose_name_plural, u'Mock models')
        self.assertEqual(self.extra_data_sr.pk, '1')
        self.assertEqual(self.extra_data_sr.score, 3)
        self.assertEqual(self.extra_data_sr.stored, 'I am stored data. How fun.')
        
        self.assertEqual(self.no_overwrite_data_sr.app_label, 'haystack')
        self.assertEqual(self.no_overwrite_data_sr.model_name, 'mockmodel')
        self.assertEqual(self.no_overwrite_data_sr.model, MockModel)
        self.assertEqual(self.no_overwrite_data_sr.verbose_name, u'Mock model')
        self.assertEqual(self.no_overwrite_data_sr.verbose_name_plural, u'Mock models')
        self.assertEqual(self.no_overwrite_data_sr.pk, '1')
        self.assertEqual(self.no_overwrite_data_sr.score, 4)
        self.assertEqual(self.no_overwrite_data_sr.stored, 'I am stored data. How fun.')
    
    def test_get_additional_fields(self):
        self.assertEqual(self.no_data_sr.get_additional_fields(), {})
        self.assertEqual(self.extra_data_sr.get_additional_fields(), {'stored': 'I am stored data. How fun.'})
        self.assertEqual(self.no_overwrite_data_sr.get_additional_fields(), {'django_ct': 'haystack.anothermockmodel', 'django_id': 2, 'stored': 'I am stored data. How fun.'})
    
    def test_unicode(self):
        self.assertEqual(self.no_data_sr.__unicode__(), u"<SearchResult: haystack.mockmodel (pk='1')>")
        self.assertEqual(self.extra_data_sr.__unicode__(), u"<SearchResult: haystack.mockmodel (pk='1')>")
        self.assertEqual(self.no_overwrite_data_sr.__unicode__(), u"<SearchResult: haystack.mockmodel (pk='1')>")
    
    def test_stored_fields(self):
        # Stow.
        import haystack
        from haystack.sites import SearchSite
        old_site = haystack.site
        test_site = SearchSite()
        haystack.site = test_site
        
        # Without registering, we should receive an empty dict.
        self.assertEqual(self.no_data_sr.get_stored_fields(), {})
        self.assertEqual(self.extra_data_sr.get_stored_fields(), {})
        self.assertEqual(self.no_overwrite_data_sr.get_stored_fields(), {})
        
        from haystack import indexes
        
        class TestSearchIndex(indexes.SearchIndex):
            stored = indexes.CharField(model_attr='author', document=True)
        
        # Register the index & try again.
        haystack.site.register(MockModel, TestSearchIndex)
        
        self.assertEqual(self.no_data_sr.get_stored_fields(), {'stored': None})
        self.assertEqual(self.extra_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})
        self.assertEqual(self.no_overwrite_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})
        
        # Restore.
        haystack.site = old_site
