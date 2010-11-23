import logging
import pickle
from django.test import TestCase
from haystack.models import SearchResult
from core.models import MockModel
from core.tests.mocks import MockSearchResult


class CaptureHandler(logging.Handler):
    logs_seen = []
    
    def emit(self, record):
        CaptureHandler.logs_seen.append(record)


class SearchResultTestCase(TestCase):
    def setUp(self):
        super(SearchResultTestCase, self).setUp()
        cap = CaptureHandler()
        logging.getLogger('haystack').addHandler(cap)
        
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
    
    def test_content_type(self):
        self.assertEqual(self.no_data_sr.content_type(), u'core.mockmodel')
        self.assertEqual(self.extra_data_sr.content_type(), u'core.mockmodel')
        self.assertEqual(self.no_overwrite_data_sr.content_type(), u'core.mockmodel')
    
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
        
        from haystack.indexes import SearchIndex, CharField
        
        class TestSearchIndex(SearchIndex):
            stored = CharField(model_attr='author', document=True)
        
        # Register the index & try again.
        haystack.site.register(MockModel, TestSearchIndex)
        
        self.assertEqual(self.no_data_sr.get_stored_fields(), {'stored': None})
        self.assertEqual(self.extra_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})
        self.assertEqual(self.no_overwrite_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})
        
        # Restore.
        haystack.site = old_site
    
    def test_missing_object(self):
        awol1 = SearchResult('core', 'mockmodel', '1000000', 2)
        self.assertEqual(awol1.app_label, 'core')
        self.assertEqual(awol1.model_name, 'mockmodel')
        self.assertEqual(awol1.pk, '1000000')
        self.assertEqual(awol1.score, 2)
        
        awol2 = SearchResult('core', 'yetanothermockmodel', '1000000', 2)
        self.assertEqual(awol2.app_label, 'core')
        self.assertEqual(awol2.model_name, 'yetanothermockmodel')
        self.assertEqual(awol2.pk, '1000000')
        self.assertEqual(awol2.score, 2)
        
        # Failed lookups should fail gracefully.
        CaptureHandler.logs_seen = []
        self.assertEqual(awol1.model, MockModel)
        self.assertEqual(awol1.object, None)
        self.assertEqual(awol1.verbose_name, u'Mock model')
        self.assertEqual(awol1.verbose_name_plural, u'Mock models')
        self.assertEqual(awol1.stored, None)
        self.assertEqual(len(CaptureHandler.logs_seen), 4)
        
        CaptureHandler.logs_seen = []
        self.assertEqual(awol2.model, None)
        self.assertEqual(awol2.object, None)
        self.assertEqual(awol2.verbose_name, u'')
        self.assertEqual(awol2.verbose_name_plural, u'')
        self.assertEqual(awol2.stored, None)
        self.assertEqual(len(CaptureHandler.logs_seen), 12)
    
    def test_pickling(self):
        pickle_me_1 = SearchResult('core', 'mockmodel', '1000000', 2)
        picklicious = pickle.dumps(pickle_me_1)
        
        pickle_me_2 = pickle.loads(picklicious)
        self.assertEqual(pickle_me_1.app_label, pickle_me_2.app_label)
        self.assertEqual(pickle_me_1.model_name, pickle_me_2.model_name)
        self.assertEqual(pickle_me_1.pk, pickle_me_2.pk)
        self.assertEqual(pickle_me_1.score, pickle_me_2.score)
