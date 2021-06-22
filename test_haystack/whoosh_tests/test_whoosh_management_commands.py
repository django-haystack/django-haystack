import datetime
import os
import unittest
from io import StringIO
from tempfile import mkdtemp
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command as real_call_command
from django.core.management.base import CommandError
from django.test import TestCase
from whoosh.qparser import QueryParser

from haystack import connections, constants, indexes
from haystack.utils.loading import UnifiedIndex

from ..core.models import MockModel
from .test_whoosh_backend import WhooshMockSearchIndex
from .testcases import WhooshTestCase


def call_command(*args, **kwargs):
    kwargs["using"] = ["whoosh"]
    print(args, kwargs)
    real_call_command(*args, **kwargs)


class ManagementCommandTestCase(WhooshTestCase):
    fixtures = ["bulk_data"]

    def setUp(self):
        super().setUp()

        self.old_ui = connections["whoosh"].get_unified_index()
        self.ui = UnifiedIndex()
        self.wmmi = WhooshMockSearchIndex()
        self.ui.build(indexes=[self.wmmi])
        self.sb = connections["whoosh"].get_backend()
        connections["whoosh"]._index = self.ui

        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.sb.delete_index()

        self.sample_objs = MockModel.objects.all()

    def tearDown(self):
        connections["whoosh"]._index = self.old_ui
        super().tearDown()

    def verify_indexed_document_count(self, expected):
        with self.raw_whoosh.searcher() as searcher:
            count = searcher.doc_count()
            self.assertEqual(count, expected)

    def verify_indexed_documents(self):
        """Confirm that the documents in the search index match the database"""

        with self.raw_whoosh.searcher() as searcher:
            count = searcher.doc_count()
            self.assertEqual(count, 23)

            indexed_doc_ids = set(i["id"] for i in searcher.documents())
            expected_doc_ids = set(
                "core.mockmodel.%d" % i
                for i in MockModel.objects.values_list("pk", flat=True)
            )
            self.assertSetEqual(indexed_doc_ids, expected_doc_ids)

    def test_basic_commands(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.verify_indexed_document_count(0)

        call_command("update_index", verbosity=0)
        self.verify_indexed_documents()

        call_command("clear_index", interactive=False, verbosity=0)
        self.verify_indexed_document_count(0)

        call_command("rebuild_index", interactive=False, verbosity=0)
        self.verify_indexed_documents()

    def test_remove(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.verify_indexed_document_count(0)

        call_command("update_index", verbosity=0)
        self.verify_indexed_documents()

        # Remove several instances.
        MockModel.objects.get(pk=1).delete()
        MockModel.objects.get(pk=2).delete()
        MockModel.objects.get(pk=8).delete()
        self.verify_indexed_document_count(23)

        # Plain ``update_index`` doesn't fix it.
        call_command("update_index", verbosity=0)
        self.verify_indexed_document_count(23)

        # … but remove does:
        call_command("update_index", remove=True, verbosity=0)
        self.verify_indexed_document_count(20)

    def test_multiprocessing(self):
        call_command("clear_index", interactive=False, verbosity=0)
        self.verify_indexed_document_count(0)

        call_command("update_index", verbosity=2, workers=2, batchsize=5)
        self.verify_indexed_documents()
