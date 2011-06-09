from django.conf import settings
from django.test import TestCase
from haystack import connections, connection_router
from haystack.query import SearchQuerySet
from haystack.utils.loading import UnifiedIndex
from discovery.models import Foo
from discovery.search_indexes import FooIndex, BarIndex


class ManualDiscoveryTestCase(TestCase):
    def test_discovery(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        ui = connections['default'].get_unified_index()
        self.assertEqual(len(ui.get_indexed_models()), 2)
        
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
        self.assertEqual(len(ui.get_indexed_models()), 2)
        
        # Test exclusions.
        ui.excluded_indexes = ['discovery.search_indexes.BarIndex']
        ui.build()
        
        self.assertEqual(len(ui.get_indexed_models()), 1)
        
        ui.excluded_indexes = ['discovery.search_indexes.BarIndex', 'discovery.search_indexes.FooIndex']
        ui.build()
        
        self.assertEqual(len(ui.get_indexed_models()), 0)
        connections['default']._index = old_ui
    
    def test_signal_setup_handling(self):
        old_ui = connections['default'].get_unified_index()
        connections['default']._index = UnifiedIndex()
        self.assertEqual(connections['default'].get_unified_index()._indexes_setup, False)
        foo_1 = Foo.objects.create(
            title='chekin sigalz',
            body='stuff'
        )
        fi = connections['default'].get_unified_index().get_index(Foo)
        fi.clear()
        fi.update()
        
        sqs = SearchQuerySet()
        existing_foo = sqs.filter(id='discovery.foo.1')[0]
        self.assertEqual(existing_foo.text, u'stuff')
        
        fi.clear()
        foo_1 = Foo.objects.get(pk=1)
        foo_1.title = 'Checking signals'
        foo_1.body = 'Stuff.'
        # This save should trigger an update.
        foo_1.save()
        self.assertEqual(connections['default'].get_unified_index()._indexes_setup, True)
        
        sqs = SearchQuerySet()
        new_foo = sqs.filter(id='discovery.foo.1')[0]
        self.assertEqual(new_foo.text, u'Stuff.')
        connections['default']._index = old_ui
