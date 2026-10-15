from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from haystack import connections, constants, indexes
from haystack.utils.loading import UnifiedIndex

from ..core.models import MockModel, MockTag


class CustomIdMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr="author")
    # The model primary key is named "id". A custom HAYSTACK_ID_FIELD no longer
    # reserves that name, so the index can store the integer pk beside it.
    id = indexes.IntegerField(model_attr="pk")

    def get_model(self):
        return MockModel


class UpdateIndexCustomIdTests(TestCase):
    def setUp(self):
        super().setUp()
        if getattr(settings, "HAYSTACK_ID_FIELD", "id") == "id":
            self.skipTest(
                "Requires DJANGO_SETTINGS_MODULE=test_haystack.whoosh_custom_id_settings."
            )

        self.ui = UnifiedIndex()
        self.ui.build(indexes=[CustomIdMockSearchIndex()])
        self.conn = connections["default"]
        self.old_index = self.conn._index
        self.conn._index = self.ui
        backend = self.conn.get_backend()
        backend.setup()

    def tearDown(self):
        if hasattr(self, "conn"):
            self.conn._index = self.old_index
        super().tearDown()

    def stored_documents(self):
        backend = self.conn.get_backend()
        backend.index = backend.index.refresh()
        with backend.index.searcher() as searcher:
            return list(searcher.documents())

    def test_remove_clears_stale_docs_when_id_field_is_not_id(self):
        self.assertEqual(constants.ID, "haystack_id")

        tag = MockTag.objects.create(name="t")
        obj = MockModel.objects.create(author="ada", tag=tag)
        call_command("update_index", "core", using=["default"], verbosity=0)

        docs = self.stored_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0][constants.ID], "core.mockmodel.%s" % obj.pk)
        self.assertEqual(docs[0]["id"], obj.pk)

        obj.delete()
        self.assertEqual(len(self.stored_documents()), 1)

        call_command(
            "update_index", "core", remove=True, using=["default"], verbosity=0
        )
        self.assertEqual(self.stored_documents(), [])
