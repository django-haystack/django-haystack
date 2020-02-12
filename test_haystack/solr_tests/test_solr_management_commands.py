# encoding: utf-8
import datetime
import os
from tempfile import mkdtemp
from unittest.mock import patch

import pysolr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from haystack import connections, constants, indexes
from haystack.utils.loading import UnifiedIndex

from ..core.models import MockModel, MockTag

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class SolrMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="author", faceted=True)
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return MockModel

    def get_updated_field(self):
        return "pub_date"


class SolrMockTagSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr="name")

    def get_model(self):
        return MockTag


class SolrMockSecretKeySearchIndex(indexes.SearchIndex, indexes.Indexable):
    Th3S3cr3tK3y = indexes.CharField(document=True, model_attr="author")

    def get_model(self):
        return MockModel


class ManagementCommandTestCase(TestCase):
    fixtures = ["base_data.json", "bulk_data.json"]

    def setUp(self):
        super(ManagementCommandTestCase, self).setUp()
        self.solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS["solr"]["URL"])

        # Stow.
        self.old_ui = connections["solr"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["solr"]._index = self.ui

    def tearDown(self):
        connections["solr"]._index = self.old_ui
        super(ManagementCommandTestCase, self).tearDown()

    def verify_indexed_documents(self):
        """Confirm that the documents in the search index match the database"""

        res = self.solr.search("*:*", fl=["id"], rows=50)
        self.assertEqual(res.hits, 23)

        indexed_doc_ids = set(i["id"] for i in res.docs)
        expected_doc_ids = set(
            "core.mockmodel.%d" % i
            for i in MockModel.objects.values_list("pk", flat=True)
        )

        self.assertSetEqual(indexed_doc_ids, expected_doc_ids)

    def test_basic_commands(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=0, commit=False)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=0)
        self.verify_indexed_documents()

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("rebuild_index", interactive=False, verbosity=0, commit=False)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("rebuild_index", interactive=False, verbosity=0, commit=True)
        self.verify_indexed_documents()

        call_command("clear_index", interactive=False, verbosity=0, commit=False)
        self.verify_indexed_documents()

    def test_remove(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=0)
        self.verify_indexed_documents()

        # Remove several instances, two of which will fit in the same block:
        MockModel.objects.get(pk=1).delete()
        MockModel.objects.get(pk=2).delete()
        MockModel.objects.get(pk=8).delete()
        self.assertEqual(self.solr.search("*:*").hits, 23)

        # Plain ``update_index`` doesn't fix it.
        call_command("update_index", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 23)

        # Remove without commit also doesn't affect queries:
        call_command(
            "update_index", remove=True, verbosity=0, batchsize=2, commit=False
        )
        self.assertEqual(self.solr.search("*:*").hits, 23)

        # … but remove with commit does:
        call_command("update_index", remove=True, verbosity=0, batchsize=2)
        self.assertEqual(self.solr.search("*:*").hits, 20)

    def test_age(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        start = datetime.datetime.now() - datetime.timedelta(hours=3)
        end = datetime.datetime.now()

        mock = MockModel.objects.get(pk=1)
        mock.pub_date = datetime.datetime.now() - datetime.timedelta(hours=2)
        mock.save()
        self.assertEqual(
            MockModel.objects.filter(pub_date__range=(start, end)).count(), 1
        )

        call_command("update_index", age=3, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 1)

    def test_age_with_time_zones(self):
        """Haystack should use django.utils.timezone.now"""
        from django.utils.timezone import now as django_now
        from haystack.management.commands.update_index import now as haystack_now

        self.assertIs(
            haystack_now,
            django_now,
            msg="update_index should use django.utils.timezone.now",
        )

        with patch("haystack.management.commands.update_index.now") as m:
            m.return_value = django_now()
            self.test_age()
            assert m.called

    def test_dates(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        start = datetime.datetime.now() - datetime.timedelta(hours=5, minutes=30)
        end = datetime.datetime.now() - datetime.timedelta(hours=2)

        mock_1 = MockModel.objects.get(pk=1)
        mock_1.pub_date = datetime.datetime.now() - datetime.timedelta(
            hours=5, minutes=1
        )
        mock_1.save()
        mock_2 = MockModel.objects.get(pk=2)
        mock_2.pub_date = datetime.datetime.now() - datetime.timedelta(hours=3)
        mock_2.save()
        mock_3 = MockModel.objects.get(pk=3)
        mock_3.pub_date = datetime.datetime.now() - datetime.timedelta(hours=1)
        mock_3.save()
        self.assertEqual(
            MockModel.objects.filter(pub_date__range=(start, end)).count(), 2
        )

        call_command(
            "update_index",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            verbosity=0,
        )
        self.assertEqual(self.solr.search("*:*").hits, 2)

    def test_multiprocessing(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=2, workers=2, batchsize=5)
        self.verify_indexed_documents()

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=2, workers=2, batchsize=5, commit=False)
        self.assertEqual(self.solr.search("*:*").hits, 0)

    def test_build_schema_wrong_backend(self):

        settings.HAYSTACK_CONNECTIONS["whoosh"] = {
            "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
            "PATH": mkdtemp(prefix="dummy-path-"),
        }

        connections["whoosh"]._index = self.ui
        self.assertRaises(
            ImproperlyConfigured, call_command, "build_solr_schema", using="whoosh"
        )

    def test_build_schema(self):

        # Stow.
        oldhdf = constants.DOCUMENT_FIELD
        oldui = connections["solr"].get_unified_index()
        oldurl = settings.HAYSTACK_CONNECTIONS["solr"]["URL"]

        try:
            needle = "Th3S3cr3tK3y"
            constants.DOCUMENT_FIELD = (
                needle
            )  # Force index to use new key for document_fields
            settings.HAYSTACK_CONNECTIONS["solr"]["URL"] = (
                settings.HAYSTACK_CONNECTIONS["solr"]["URL"].rsplit("/", 1)[0] + "/mgmnt"
            )

            ui = UnifiedIndex()
            ui.build(indexes=[SolrMockSecretKeySearchIndex()])
            connections["solr"]._index = ui

            rendered_file = StringIO()

            script_dir = os.path.realpath(os.path.dirname(__file__))
            conf_dir = os.path.join(
                script_dir, "server", "solr", "server", "solr", "mgmnt", "conf"
            )
            schema_file = os.path.join(conf_dir, "schema.xml")
            solrconfig_file = os.path.join(conf_dir, "solrconfig.xml")

            self.assertTrue(
                os.path.isdir(conf_dir), msg="Expected %s to be a directory" % conf_dir
            )

            call_command("build_solr_schema", using="solr", stdout=rendered_file)
            contents = rendered_file.getvalue()
            self.assertGreater(contents.find('name="%s' % needle), -1)

            call_command("build_solr_schema", using="solr", configure_directory=conf_dir)
            with open(schema_file) as s:
                self.assertGreater(s.read().find('name="%s' % needle), -1)
            with open(solrconfig_file) as s:
                self.assertGreater(s.read().find('name="df">%s' % needle), -1)

            self.assertTrue(os.path.isfile(os.path.join(conf_dir, "managed-schema.old")))

            call_command("build_solr_schema", using="solr", reload_core=True)

            os.rename(schema_file, "%s.bak" % schema_file)
            self.assertRaises(
                CommandError,
                call_command,
                "build_solr_schema",
                using="solr",
                reload_core=True,
            )

            call_command("build_solr_schema", using="solr", filename=schema_file)
            with open(schema_file) as s:
                self.assertGreater(s.read().find('name="%s' % needle), -1)
        finally:
            # reset
            constants.DOCUMENT_FIELD = oldhdf
            connections["solr"]._index = oldui
            settings.HAYSTACK_CONNECTIONS["solr"]["URL"] = oldurl


class AppModelManagementCommandTestCase(TestCase):
    fixtures = ["base_data", "bulk_data.json"]

    def setUp(self):
        super(AppModelManagementCommandTestCase, self).setUp()
        self.solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS["solr"]["URL"])

        # Stow.
        self.old_ui = connections["solr"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.smtmi = SolrMockTagSearchIndex()
        self.ui.build(indexes=[self.smmi, self.smtmi])
        connections["solr"]._index = self.ui

    def tearDown(self):
        connections["solr"]._index = self.old_ui
        super(AppModelManagementCommandTestCase, self).tearDown()

    def test_app_model_variations(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 25)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", "core", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 25)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        with self.assertRaises(ImproperlyConfigured):
            call_command("update_index", "fake_app_thats_not_there")

        call_command("update_index", "core", "discovery", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 25)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", "discovery", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", "core.MockModel", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 23)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", "core.MockTag", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 2)

        call_command("clear_index", interactive=False, verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 0)

        call_command("update_index", "core.MockTag", "core.MockModel", verbosity=0)
        self.assertEqual(self.solr.search("*:*").hits, 25)
