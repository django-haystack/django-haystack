import logging as std_logging
import pickle
import django
from django.test import TestCase
from django.utils import unittest
from haystack import connections
from haystack.models import SearchResult
from haystack.utils import log as logging
from haystack.utils.loading import UnifiedIndex
from test_haystack.core.models import MockModel, AFifthMockModel
from .mocks import MockSearchResult
from .test_indexes import ReadQuerySetTestSearchIndex


class CaptureHandler(std_logging.Handler):
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
        old_unified_index = connections['default']._index
        ui = UnifiedIndex()
        ui.build(indexes=[])
        connections['default']._index = ui

        # Without registering, we should receive an empty dict.
        self.assertEqual(self.no_data_sr.get_stored_fields(), {})
        self.assertEqual(self.extra_data_sr.get_stored_fields(), {})
        self.assertEqual(self.no_overwrite_data_sr.get_stored_fields(), {})

        from haystack import indexes

        class TestSearchIndex(indexes.SearchIndex, indexes.Indexable):
            stored = indexes.CharField(model_attr='author', document=True)

            def get_model(self):
                return MockModel

        # Include the index & try again.
        ui.document_field = 'stored'
        ui.build(indexes=[TestSearchIndex()])

        self.assertEqual(self.no_data_sr.get_stored_fields(), {'stored': None})
        self.assertEqual(self.extra_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})
        self.assertEqual(self.no_overwrite_data_sr.get_stored_fields(), {'stored': 'I am stored data. How fun.'})

        # Restore.
        connections['default']._index = old_unified_index

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

    if django.get_version() == '1.7':
        # FIXME: https://github.com/toastdriven/django-haystack/issues/1069
        test_missing_object = unittest.expectedFailure(test_missing_object)

    def test_read_queryset(self):
        # The model is flagged deleted so not returned by the default manager.
        deleted1 = SearchResult('core', 'afifthmockmodel', 2, 2)
        self.assertEqual(deleted1.object, None)

        # Stow.
        old_unified_index = connections['default']._index
        ui = UnifiedIndex()
        ui.document_field = 'author'
        ui.build(indexes=[ReadQuerySetTestSearchIndex()])
        connections['default']._index = ui

        # The soft delete manager returns the object.
        deleted2 = SearchResult('core', 'afifthmockmodel', 2, 2)
        self.assertNotEqual(deleted2.object, None)
        self.assertEqual(deleted2.object.author, 'sam2')

        # Restore.
        connections['default']._index = old_unified_index

    def test_pickling(self):
        pickle_me_1 = SearchResult('core', 'mockmodel', '1000000', 2)
        picklicious = pickle.dumps(pickle_me_1)

        pickle_me_2 = pickle.loads(picklicious)
        self.assertEqual(pickle_me_1.app_label, pickle_me_2.app_label)
        self.assertEqual(pickle_me_1.model_name, pickle_me_2.model_name)
        self.assertEqual(pickle_me_1.pk, pickle_me_2.pk)
        self.assertEqual(pickle_me_1.score, pickle_me_2.score)
