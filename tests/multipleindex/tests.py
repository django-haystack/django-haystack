import shutil
from django.conf import settings
from django.test import TestCase
from haystack import connections, connection_router
from haystack.exceptions import NotHandled
from haystack.query import SearchQuerySet
from haystack.utils.loading import UnifiedIndex
from multipleindex.search_indexes import FooIndex
from multipleindex.models import Foo, Bar


class MultipleIndexTestCase(TestCase):
    def setUp(self):
        super(MultipleIndexTestCase, self).setUp()
        self.ui = connections['default'].get_unified_index()
        self.fi = self.ui.get_index(Foo)
        self.bi = self.ui.get_index(Bar)
        self.solr_backend = connections['default'].get_backend()
        self.whoosh_backend = connections['whoosh'].get_backend()

        foo_1 = Foo.objects.create(
            title='Haystack test',
            body='foo 1',
        )
        foo_2 = Foo.objects.create(
            title='Another Haystack test',
            body='foo 2',
        )
        bar_1 = Bar.objects.create(
            author='Haystack test',
            content='bar 1',
        )
        bar_2 = Bar.objects.create(
            author='Another Haystack test',
            content='bar 2',
        )
        bar_3 = Bar.objects.create(
            author='Yet another Haystack test',
            content='bar 3',
        )

        self.fi.reindex(using='default')
        self.fi.reindex(using='whoosh')
        self.bi.reindex(using='default')

    def tearDown(self):
        self.fi.clear()
        self.bi.clear()
        # Because Whoosh doesn't clean up its mess.
        shutil.rmtree(settings.HAYSTACK_CONNECTIONS['whoosh']['PATH'])
        super(MultipleIndexTestCase, self).setUp()

    def test_index_update_object_using(self):
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        foo_3 = Foo.objects.create(
            title='Whee another Haystack test',
            body='foo 3',
        )

        self.fi.update_object(foo_3)
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 3)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        self.fi.update_object(foo_3, using='whoosh')
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 3)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 3)

    def test_index_remove_object_using(self):
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        foo_1 = Foo.objects.get(pk=1)

        self.fi.remove_object(foo_1)
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 1)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        self.fi.remove_object(foo_1, using='whoosh')
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 1)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 1)

    def test_index_clear_using(self):
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        self.fi.clear()
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 0)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        self.fi.clear(using='whoosh')
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 0)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 0)

    def test_index_update_using(self):
        self.fi.clear()
        self.fi.clear(using='whoosh')
        self.bi.clear()
        self.bi.clear(using='whoosh')

        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 0)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 0)

        self.fi.update()
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 0)

        self.fi.update(using='whoosh')
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

    def test_searchqueryset_using(self):
        # Using the default.
        sqs = SearchQuerySet()
        self.assertEqual(sqs.count(), 5)
        self.assertEqual(sqs.models(Foo).count(), 2)
        self.assertEqual(sqs.models(Bar).count(), 3)

        self.assertEqual(sqs.using('default').count(), 5)
        self.assertEqual(sqs.using('default').models(Foo).count(), 2)
        self.assertEqual(sqs.using('default').models(Bar).count(), 3)

        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Bar).count(), 0)

    def test_searchquery_using(self):
        sq = connections['default'].get_query()

        # Using the default.
        self.assertEqual(sq.get_count(), 5)

        # "Swap" to the default.
        sq = sq.using('default')
        self.assertEqual(sq.get_count(), 5)

        # Swap the ``SearchQuery`` used.
        sq = sq.using('whoosh')
        self.assertEqual(sq.get_count(), 2)

    def test_excluded_indexes(self):
        wui = connections['whoosh'].get_unified_index()
        self.assertEqual(len(wui.collect_indexes()), 1)
        self.assertTrue(isinstance(wui.collect_indexes()[0], FooIndex))

        # Shouldn't error.
        wui.get_index(Foo)

        # Should error, since it's not present.
        self.assertRaises(NotHandled, wui.get_index, Bar)
