from django.test import TestCase
from haystack.backends.simple_backend import SearchBackend, SearchQuery
from haystack.query import SQ


class SimpleSearchQueryTestCase(TestCase):
    def setUp(self):
        super(SimpleSearchQueryTestCase, self).setUp()
        self.sq = SearchQuery(backend=SearchBackend())

    def test_build_query_all(self):
        self.assertEqual(self.sq.build_query(), '*')

    def test_build_query_single_word(self):
        self.sq.add_filter(SQ(content='hello'))
        self.assertEqual(self.sq.build_query(), 'hello')

    def test_build_query_multiple_word(self):
        self.sq.add_filter(SQ(name='foo'))
        self.sq.add_filter(SQ(name='bar'))
        self.assertEqual(self.sq.build_query(), 'foo bar')
        