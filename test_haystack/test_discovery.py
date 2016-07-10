# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase
from test_haystack.discovery.search_indexes import FooIndex

from haystack import connections
from haystack.utils.loading import UnifiedIndex

EXPECTED_INDEX_MODEL_COUNT = 6


class ManualDiscoveryTestCase(TestCase):
    def test_discovery(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        ui = connections['default'].get_unified_index()
        self.assertEqual(len(ui.get_indexed_models()), EXPECTED_INDEX_MODEL_COUNT)

        ui.build(indexes=[FooIndex()])

        self.assertListEqual(['discovery.foo'],
                             [str(i._meta) for i in ui.get_indexed_models()])

        ui.build(indexes=[])

        self.assertListEqual([], ui.get_indexed_models())
        connections['default']._index = old_ui


class AutomaticDiscoveryTestCase(TestCase):
    def test_discovery(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        ui = connections['default'].get_unified_index()
        self.assertEqual(len(ui.get_indexed_models()), EXPECTED_INDEX_MODEL_COUNT)

        # Test exclusions.
        ui.excluded_indexes = ['test_haystack.discovery.search_indexes.BarIndex']
        ui.build()

        indexed_model_names = [str(i._meta) for i in ui.get_indexed_models()]
        self.assertIn('multipleindex.foo', indexed_model_names)
        self.assertIn('multipleindex.bar', indexed_model_names)
        self.assertNotIn('discovery.bar', indexed_model_names)

        ui.excluded_indexes = ['test_haystack.discovery.search_indexes.BarIndex',
                               'test_haystack.discovery.search_indexes.FooIndex']
        ui.build()

        indexed_model_names = [str(i._meta) for i in ui.get_indexed_models()]
        self.assertIn('multipleindex.foo', indexed_model_names)
        self.assertIn('multipleindex.bar', indexed_model_names)
        self.assertListEqual([], [i for i in indexed_model_names if i.startswith('discovery')])
        connections['default']._index = old_ui
