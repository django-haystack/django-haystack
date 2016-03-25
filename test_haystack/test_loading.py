# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from test_haystack.core.models import AnotherMockModel, MockModel

from haystack import indexes
from haystack.exceptions import NotHandled, SearchFieldError
from haystack.utils import loading

try:
    import pysolr
except ImportError:
    pysolr = False


class ConnectionHandlerTestCase(TestCase):
    def test_init(self):
        ch = loading.ConnectionHandler({})
        self.assertEqual(ch.connections_info, {})

        ch = loading.ConnectionHandler({
            'default': {
                'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
                'URL': 'http://localhost:9001/solr/test_default',
            },
        })
        self.assertEqual(ch.connections_info, {
            'default': {
                'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
                'URL': 'http://localhost:9001/solr/test_default',
            },
        })

    @unittest.skipIf(pysolr is False, "pysolr required")
    def test_get_item(self):
        ch = loading.ConnectionHandler({})

        try:
            empty_engine = ch['default']
            self.fail()
        except ImproperlyConfigured:
            pass

        ch = loading.ConnectionHandler({
            'default': {
                'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
                'URL': 'http://localhost:9001/solr/test_default',
            },
        })
        solr_engine = ch['default']
        backend_path, memory_address = repr(solr_engine).strip('<>').split(' object at ')
        self.assertEqual(backend_path, 'haystack.backends.solr_backend.SolrEngine')

        solr_engine_2 = ch['default']
        backend_path_2, memory_address_2 = repr(solr_engine_2).strip('<>').split(' object at ')
        self.assertEqual(backend_path_2, 'haystack.backends.solr_backend.SolrEngine')
        # Ensure we're loading out of the memorized connection.
        self.assertEqual(memory_address_2, memory_address)

        try:
            empty_engine = ch['slave']
            self.fail()
        except ImproperlyConfigured:
            pass

    def test_get_unified_index(self):
        ch = loading.ConnectionHandler({
            'default': {
                'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
            }
        })
        ui = ch['default'].get_unified_index()
        klass, address = repr(ui).strip('<>').split(' object at ')
        self.assertEqual(str(klass), 'haystack.utils.loading.UnifiedIndex')

        ui_2 = ch['default'].get_unified_index()
        klass_2, address_2 = repr(ui_2).strip('<>').split(' object at ')
        self.assertEqual(str(klass_2), 'haystack.utils.loading.UnifiedIndex')
        self.assertEqual(address_2, address)


class ConnectionRouterTestCase(TestCase):
    @override_settings()
    def test_init(self):
        del settings.HAYSTACK_ROUTERS
        cr = loading.ConnectionRouter()
        self.assertEqual([str(route.__class__) for route in cr.routers], ["<class 'haystack.routers.DefaultRouter'>"])

    @override_settings(HAYSTACK_ROUTERS=['haystack.routers.DefaultRouter'])
    def test_router_override1(self):
        cr = loading.ConnectionRouter()
        self.assertEqual([str(route.__class__) for route in cr.routers], ["<class 'haystack.routers.DefaultRouter'>"])

    @override_settings(HAYSTACK_ROUTERS=[])
    def test_router_override2(self):
        cr = loading.ConnectionRouter()
        self.assertEqual([str(route.__class__) for route in cr.routers], ["<class 'haystack.routers.DefaultRouter'>"])

    @override_settings(HAYSTACK_ROUTERS=['test_haystack.mocks.MockMasterSlaveRouter', 'haystack.routers.DefaultRouter'])
    def test_router_override3(self):
        cr = loading.ConnectionRouter()
        self.assertEqual([str(route.__class__) for route in cr.routers], ["<class 'test_haystack.mocks.MockMasterSlaveRouter'>", "<class 'haystack.routers.DefaultRouter'>"])

    @override_settings()
    def test_actions1(self):
        del settings.HAYSTACK_ROUTERS
        cr = loading.ConnectionRouter()
        self.assertEqual(cr.for_read(), 'default')
        self.assertEqual(cr.for_write(), ['default'])

    @override_settings(HAYSTACK_ROUTERS=['test_haystack.mocks.MockMasterSlaveRouter', 'haystack.routers.DefaultRouter'])
    def test_actions2(self):
        cr = loading.ConnectionRouter()
        self.assertEqual(cr.for_read(), 'slave')
        self.assertEqual(cr.for_write(), ['master', 'default'])

    @override_settings(HAYSTACK_ROUTERS=['test_haystack.mocks.MockPassthroughRouter', 'test_haystack.mocks.MockMasterSlaveRouter', 'haystack.routers.DefaultRouter'])
    def test_actions3(self):
        cr = loading.ConnectionRouter()
        # Demonstrate pass-through
        self.assertEqual(cr.for_read(), 'slave')
        self.assertEqual(cr.for_write(), ['master', 'default'])
        # Demonstrate that hinting can change routing.
        self.assertEqual(cr.for_read(pass_through=False), 'pass')
        self.assertEqual(cr.for_write(pass_through=False), ['pass', 'master', 'default'])

    @override_settings(HAYSTACK_ROUTERS=['test_haystack.mocks.MockMultiRouter', 'haystack.routers.DefaultRouter'])
    def test_actions4(self):
        cr = loading.ConnectionRouter()
        # Demonstrate that a router can return multiple backends in the "for_write" method
        self.assertEqual(cr.for_read(), 'default')
        self.assertEqual(cr.for_write(), ['multi1', 'multi2', 'default'])


class MockNotAModel(object):
    pass


class FakeSearchIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def update_object(self, instance, **kwargs):
        # Incorrect behavior but easy to test and all we care about is that we
        # make it here. We rely on the `SearchIndex` tests to ensure correct
        # behavior.
        return True

    def remove_object(self, instance, **kwargs):
        # Incorrect behavior but easy to test and all we care about is that we
        # make it here. We rely on the `SearchIndex` tests to ensure correct
        # behavior.
        return True

    def get_model(self):
        return MockModel


class InvalidSearchIndex(indexes.SearchIndex, indexes.Indexable):
    document = indexes.CharField(document=True)

    def get_model(self):
        return MockModel


class BasicMockModelSearchIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def get_model(self):
        return MockModel


class BasicAnotherMockModelSearchIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def get_model(self):
        return AnotherMockModel


class ValidSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    author = indexes.CharField(index_fieldname='name')
    title = indexes.CharField(indexed=False)

    def get_model(self):
        return MockModel


class AlternateValidSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    author = indexes.CharField(faceted=True)
    title = indexes.CharField(faceted=True)

    def get_model(self):
        return AnotherMockModel


class ExplicitFacetSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    author = indexes.CharField(faceted=True)
    title = indexes.CharField()
    title_facet = indexes.FacetCharField(facet_for='title')
    bare_facet = indexes.FacetCharField()

    def get_model(self):
        return MockModel


class MultiValueValidSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    author = indexes.MultiValueField(stored=False)
    title = indexes.CharField(indexed=False)

    def get_model(self):
        return MockModel


class UnifiedIndexTestCase(TestCase):
    def setUp(self):
        super(UnifiedIndexTestCase, self).setUp()
        self.ui = loading.UnifiedIndex()
        self.ui.build([])

    def test_get_index(self):
        self.assertRaises(NotHandled, self.ui.get_index, MockModel)
        try:
            self.ui.get_index(MockModel)
        except NotHandled as e:
            self.assertTrue(MockModel.__name__ in str(e))

        self.ui.build(indexes=[BasicMockModelSearchIndex()])
        self.assertTrue(isinstance(self.ui.get_index(MockModel), indexes.BasicSearchIndex))

    def test_get_indexed_models(self):
        self.assertEqual(self.ui.get_indexed_models(), [])

        self.ui.build(indexes=[ValidSearchIndex()])
        indexed_models = self.ui.get_indexed_models()
        self.assertEqual(len(indexed_models), 1)
        self.assertTrue(MockModel in indexed_models)

    def test_get_indexes(self):
        self.assertEqual(self.ui.get_indexes(), {})

        index = ValidSearchIndex()
        self.ui.build(indexes=[index])

        results = self.ui.get_indexes()
        self.assertEqual(len(results), 1)
        self.assertTrue(MockModel in results)
        self.assertEqual(results[MockModel], index)

    def test_all_searchfields(self):
        self.ui.build(indexes=[BasicMockModelSearchIndex()])
        fields = self.ui.all_searchfields()
        self.assertEqual(len(fields), 1)
        self.assertTrue('text' in fields)
        self.assertTrue(isinstance(fields['text'], indexes.CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, True)

        self.ui.build(indexes=[BasicMockModelSearchIndex(), AlternateValidSearchIndex()])
        fields = self.ui.all_searchfields()
        self.assertEqual(len(fields), 5)
        self.assertEqual(sorted(fields.keys()), ['author', 'author_exact', 'text', 'title', 'title_exact'])
        self.assertTrue('text' in fields)
        self.assertTrue(isinstance(fields['text'], indexes.CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, True)
        self.assertTrue('title' in fields)
        self.assertTrue(isinstance(fields['title'], indexes.CharField))
        self.assertEqual(fields['title'].document, False)
        self.assertEqual(fields['title'].use_template, False)
        self.assertEqual(fields['title'].faceted, True)
        self.assertEqual(fields['title'].indexed, True)
        self.assertTrue('author' in fields)
        self.assertTrue(isinstance(fields['author'], indexes.CharField))
        self.assertEqual(fields['author'].document, False)
        self.assertEqual(fields['author'].use_template, False)
        self.assertEqual(fields['author'].faceted, True)
        self.assertEqual(fields['author'].stored, True)
        self.assertEqual(fields['author'].index_fieldname, 'author')

        self.ui.build(indexes=[AlternateValidSearchIndex(), MultiValueValidSearchIndex()])
        fields = self.ui.all_searchfields()
        self.assertEqual(len(fields), 5)
        self.assertEqual(sorted(fields.keys()), ['author', 'author_exact', 'text', 'title', 'title_exact'])
        self.assertTrue('text' in fields)
        self.assertTrue(isinstance(fields['text'], indexes.CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, False)
        self.assertTrue('title' in fields)
        self.assertTrue(isinstance(fields['title'], indexes.CharField))
        self.assertEqual(fields['title'].document, False)
        self.assertEqual(fields['title'].use_template, False)
        self.assertEqual(fields['title'].faceted, True)
        self.assertEqual(fields['title'].indexed, True)
        self.assertTrue('author' in fields)
        self.assertTrue(isinstance(fields['author'], indexes.MultiValueField))
        self.assertEqual(fields['author'].document, False)
        self.assertEqual(fields['author'].use_template, False)
        self.assertEqual(fields['author'].stored, True)
        self.assertEqual(fields['author'].faceted, True)
        self.assertEqual(fields['author'].index_fieldname, 'author')

        try:
            self.ui.build(indexes=[AlternateValidSearchIndex(), InvalidSearchIndex()])
            self.fail()
        except SearchFieldError:
            pass

    def test_get_index_fieldname(self):
        self.assertEqual(self.ui._fieldnames, {})

        self.ui.build(indexes=[ValidSearchIndex(), BasicAnotherMockModelSearchIndex()])
        self.ui.get_index_fieldname('text')
        self.assertEqual(self.ui._fieldnames, {'text': 'text', 'title': 'title', 'author': 'name'})
        self.assertEqual(self.ui.get_index_fieldname('text'), 'text')
        self.assertEqual(self.ui.get_index_fieldname('author'), 'name')
        self.assertEqual(self.ui.get_index_fieldname('title'), 'title')

        # Reset the internal state to test the invalid case.
        self.ui.reset()
        self.assertEqual(self.ui._fieldnames, {})

        try:
            self.ui.build(indexes=[ValidSearchIndex(), AlternateValidSearchIndex()])
            self.fail()
        except SearchFieldError:
            pass

    def test_basic_get_facet_field_name(self):
        self.assertEqual(self.ui._facet_fieldnames, {})

        self.ui.build(indexes=[BasicMockModelSearchIndex(), AlternateValidSearchIndex()])
        self.ui.get_facet_fieldname('text')
        self.assertEqual(self.ui._facet_fieldnames, {'title': 'title_exact', 'author': 'author_exact'})
        self.assertEqual(self.ui.get_index_fieldname('text'), 'text')
        self.assertEqual(self.ui.get_index_fieldname('author'), 'author')
        self.assertEqual(self.ui.get_index_fieldname('title'), 'title')

        self.assertEqual(self.ui.get_facet_fieldname('text'), 'text')
        self.assertEqual(self.ui.get_facet_fieldname('author'), 'author_exact')
        self.assertEqual(self.ui.get_facet_fieldname('title'), 'title_exact')

    def test_more_advanced_get_facet_field_name(self):
        self.assertEqual(self.ui._facet_fieldnames, {})

        self.ui.build(indexes=[BasicAnotherMockModelSearchIndex(), ExplicitFacetSearchIndex()])
        self.ui.get_facet_fieldname('text')
        self.assertEqual(self.ui._facet_fieldnames, {'bare_facet': 'bare_facet', 'title': 'title_facet', 'author': 'author_exact'})
        self.assertEqual(self.ui.get_facet_fieldname('title'), 'title_facet')
        self.assertEqual(self.ui.get_facet_fieldname('bare_facet'), 'bare_facet')
