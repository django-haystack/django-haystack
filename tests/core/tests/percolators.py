from ..models import MockModel
from ..tests.indexes import GoodMockSearchIndex

from haystack import connections
from haystack.utils.loading import UnifiedIndex
from haystack.query import SearchQuerySet

from django.test import TestCase

class PercolatorTestCase(TestCase):
    def setUp(self):
        #set up indexes
        ui = UnifiedIndex()
        gmsi = GoodMockSearchIndex()
        ui.build(indexes=[gmsi])
        connections['default']._index = ui

        # Update the "index".
        backend = connections['default'].get_backend()
        backend.clear()
        backend.update(gmsi, MockModel.objects.all())

        self.percolator_name = 'search_for_daniel2'

    def test_percolator_and_percolate(self):
        sqs = SearchQuerySet()

        #create query, create percolator
        sqs.filter(author='daniel2').save_as_percolator("search_for_daniel2")

        #percolate test object against query
        self.assertEqual(sqs.percolate(MockModel.objects.filter(author='daniel2')[:1].get())[0], self.percolator_name)
        self.assertEqual(sqs.percolate(MockModel.objects.exclude(author='daniel2')[:1].get()), [])
