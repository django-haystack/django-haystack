from django.test import TestCase

from haystack import connections
from haystack.models import SearchResult
from haystack.query import SQ


class SimpleSearchQueryTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.sq = connections["simple"].get_query()

    def test_build_query_all(self):
        self.assertEqual(self.sq.build_query(), "*")

    def test_build_query_single_word(self):
        self.sq.add_filter(SQ(content="hello"))
        self.assertEqual(self.sq.build_query(), "hello")

    def test_build_query_multiple_word(self):
        self.sq.add_filter(SQ(name="foo"))
        self.sq.add_filter(SQ(name="bar"))
        self.assertEqual(self.sq.build_query(), "foo bar")

    def test_set_result_class(self):
        # Assert that we're defaulting to ``SearchResult``.
        self.assertTrue(issubclass(self.sq.result_class, SearchResult))

        # Custom class.
        class IttyBittyResult:
            pass

        self.sq.set_result_class(IttyBittyResult)
        self.assertTrue(issubclass(self.sq.result_class, IttyBittyResult))

        # Reset to default.
        self.sq.set_result_class(None)
        self.assertTrue(issubclass(self.sq.result_class, SearchResult))
