# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from tempfile import mkdtemp

import pysolr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase
from mock import patch

from haystack import connections, indexes
from haystack.utils.loading import UnifiedIndex

from ..core.models import MockModel, MockTag


class SolrMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel

    def get_updated_field(self):
        return 'pub_date'


class SolrMockTagSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return MockTag


class ManagementCommandTestCase(TestCase):
    fixtures = ['base_data.json', 'bulk_data.json']

    def setUp(self):
        super(ManagementCommandTestCase, self).setUp()
        self.solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui

    def tearDown(self):
        connections['solr']._index = self.old_ui
        super(ManagementCommandTestCase, self).tearDown()

    def verify_indexed_documents(self):
        """Confirm that the documents in the search index match the database"""

        res = self.solr.search('*:*', fl=['id'], rows=50)
        self.assertEqual(res.hits, 23)

        indexed_doc_ids = set(i['id'] for i in res.docs)
        expected_doc_ids = set('core.mockmodel.%d' % i for i in MockModel.objects.values_list('pk', flat=True))

        self.assertSetEqual(indexed_doc_ids, expected_doc_ids)

    def test_basic_commands(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=0, commit=False)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=0)
        self.verify_indexed_documents()

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('rebuild_index', interactive=False, verbosity=0, commit=False)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('rebuild_index', interactive=False, verbosity=0, commit=True)
        self.verify_indexed_documents()

        call_command('clear_index', interactive=False, verbosity=0, commit=False)
        self.verify_indexed_documents()

    def test_remove(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=0)
        self.verify_indexed_documents()

        # Remove several instances, two of which will fit in the same block:
        MockModel.objects.get(pk=1).delete()
        MockModel.objects.get(pk=2).delete()
        MockModel.objects.get(pk=8).delete()
        self.assertEqual(self.solr.search('*:*').hits, 23)

        # Plain ``update_index`` doesn't fix it.
        call_command('update_index', verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)

        # Remove without commit also doesn't affect queries:
        call_command('update_index', remove=True, verbosity=0, batchsize=2, commit=False)
        self.assertEqual(self.solr.search('*:*').hits, 23)

        # … but remove with commit does:
        call_command('update_index', remove=True, verbosity=0, batchsize=2)
        self.assertEqual(self.solr.search('*:*').hits, 20)

    def test_age(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        start = datetime.datetime.now() - datetime.timedelta(hours=3)
        end = datetime.datetime.now()

        mock = MockModel.objects.get(pk=1)
        mock.pub_date = datetime.datetime.now() - datetime.timedelta(hours=2)
        mock.save()
        self.assertEqual(MockModel.objects.filter(pub_date__range=(start, end)).count(), 1)

        call_command('update_index', age=3, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 1)

    def test_age_with_time_zones(self):
        """Haystack should use django.utils.timezone.now"""
        from django.utils.timezone import now as django_now
        from haystack.management.commands.update_index import now as haystack_now

        self.assertIs(haystack_now, django_now,
                      msg="update_index should use django.utils.timezone.now")

        with patch("haystack.management.commands.update_index.now") as m:
            m.return_value = django_now()
            self.test_age()
            assert m.called

    def test_dates(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        start = datetime.datetime.now() - datetime.timedelta(hours=5, minutes=30)
        end = datetime.datetime.now() - datetime.timedelta(hours=2)

        mock_1 = MockModel.objects.get(pk=1)
        mock_1.pub_date = datetime.datetime.now() - datetime.timedelta(hours=5, minutes=1)
        mock_1.save()
        mock_2 = MockModel.objects.get(pk=2)
        mock_2.pub_date = datetime.datetime.now() - datetime.timedelta(hours=3)
        mock_2.save()
        mock_3 = MockModel.objects.get(pk=3)
        mock_3.pub_date = datetime.datetime.now() - datetime.timedelta(hours=1)
        mock_3.save()
        self.assertEqual(MockModel.objects.filter(pub_date__range=(start, end)).count(), 2)

        call_command('update_index', start_date=start.isoformat(), end_date=end.isoformat(), verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 2)

    def test_multiprocessing(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=2, workers=2, batchsize=5)
        self.verify_indexed_documents()

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=2, workers=2, batchsize=5, commit=False)
        self.assertEqual(self.solr.search('*:*').hits, 0)

    def test_build_schema_wrong_backend(self):

        settings.HAYSTACK_CONNECTIONS['whoosh'] = {'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
                                                   'PATH': mkdtemp(prefix='dummy-path-'), }

        connections['whoosh']._index = self.ui
        self.assertRaises(ImproperlyConfigured, call_command, 'build_solr_schema', using='whoosh', interactive=False)


class AppModelManagementCommandTestCase(TestCase):
    fixtures = ['base_data', 'bulk_data.json']

    def setUp(self):
        super(AppModelManagementCommandTestCase, self).setUp()
        self.solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.smtmi = SolrMockTagSearchIndex()
        self.ui.build(indexes=[self.smmi, self.smtmi])
        connections['solr']._index = self.ui

    def tearDown(self):
        connections['solr']._index = self.old_ui
        super(AppModelManagementCommandTestCase, self).tearDown()

    def test_app_model_variations(self):
        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 25)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', 'core', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 25)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        with self.assertRaises(ImproperlyConfigured):
            call_command('update_index', 'fake_app_thats_not_there', interactive=False)

        call_command('update_index', 'core', 'discovery', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 25)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', 'discovery', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', 'core.MockModel', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 23)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', 'core.MockTag', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 2)

        call_command('clear_index', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 0)

        call_command('update_index', 'core.MockTag', 'core.MockModel', interactive=False, verbosity=0)
        self.assertEqual(self.solr.search('*:*').hits, 25)
