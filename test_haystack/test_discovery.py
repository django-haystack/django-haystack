from django.conf import settings
from django.test import TestCase

from haystack import connections, connection_router
from haystack.query import SearchQuerySet
from haystack.utils.loading import UnifiedIndex

from test_haystack.discovery.models import Foo
from test_haystack.discovery.search_indexes import FooIndex, BarIndex


class ManualDiscoveryTestCase(TestCase):
    def test_discovery(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        ui = connections['default'].get_unified_index()
        self.assertEqual(len(ui.get_indexed_models()), 5)

        ui.build(indexes=[FooIndex()])

        self.assertEqual(len(ui.get_indexed_models()), 1)

        ui.build(indexes=[])

        self.assertEqual(len(ui.get_indexed_models()), 0)
        connections['default']._index = old_ui


class AutomaticDiscoveryTestCase(TestCase):
    def test_discovery(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        ui = connections['default'].get_unified_index()
        self.assertEqual(len(ui.get_indexed_models()), 5)

        # Test exclusions.
        ui.excluded_indexes = ['test_haystack.discovery.search_indexes.BarIndex']
        ui.build()

        self.assertEqual(len(ui.get_indexed_models()), 4)

        ui.excluded_indexes = ['test_haystack.discovery.search_indexes.BarIndex', 'test_haystack.discovery.search_indexes.FooIndex']
        ui.build()

        self.assertEqual(len(ui.get_indexed_models()), 3)
        connections['default']._index = old_ui
