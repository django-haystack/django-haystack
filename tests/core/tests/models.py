from django.test import TestCase
from haystack.models import SearchResult
from core.models import MockModel
from core.tests.mocks import MockSearchResult


class SearchResultTestCase(TestCase):
    def test_init(self):
        no_data = {}
        extra_data = {
            'stored': 'I am stored data. How fun.',
        }
        no_overwrite_data = {
            'django_id_s': 2,
            'django_ct_s': 'haystack.anothermockmodel',
            'stored': 'I am stored data. How fun.',
        }
        
        no_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 2)
        self.assertEqual(no_data_sr.app_label, 'haystack')
        self.assertEqual(no_data_sr.module_name, 'mockmodel')
        self.assertEqual(no_data_sr.model, MockModel)
        self.assertEqual(no_data_sr.pk, '1')
        self.assertEqual(no_data_sr.score, 2)
        self.assertEqual(no_data_sr.stored, None)
        
        extra_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 3, **extra_data)
        self.assertEqual(extra_data_sr.app_label, 'haystack')
        self.assertEqual(extra_data_sr.module_name, 'mockmodel')
        self.assertEqual(extra_data_sr.model, MockModel)
        self.assertEqual(extra_data_sr.pk, '1')
        self.assertEqual(extra_data_sr.score, 3)
        self.assertEqual(extra_data_sr.stored, 'I am stored data. How fun.')
        
        no_overwrite_data_sr = MockSearchResult('haystack', 'mockmodel', '1', 4, **no_overwrite_data)
        self.assertEqual(no_overwrite_data_sr.app_label, 'haystack')
        self.assertEqual(no_overwrite_data_sr.module_name, 'mockmodel')
        self.assertEqual(no_overwrite_data_sr.model, MockModel)
        self.assertEqual(no_overwrite_data_sr.pk, '1')
        self.assertEqual(no_overwrite_data_sr.score, 4)
        self.assertEqual(no_overwrite_data_sr.stored, 'I am stored data. How fun.')
