# encoding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from django.db import models

from haystack import connections
from haystack.exceptions import NotHandled
from haystack.query import SearchQuerySet
from haystack.signals import BaseSignalProcessor

from ..whoosh_tests.testcases import WhooshTestCase
from .models import Bar, Foo
from .search_indexes import BarIndex, FooIndex


class MultipleIndexTestCase(WhooshTestCase):
    def setUp(self):
        super(MultipleIndexTestCase, self).setUp()

        self.ui = connections['solr'].get_unified_index()
        self.fi = self.ui.get_index(Foo)
        self.bi = self.ui.get_index(Bar)
        self.solr_backend = connections['solr'].get_backend()
        self.whoosh_backend = connections['whoosh'].get_backend()
        self.filtered_whoosh_backend = connections['filtered_whoosh'].get_backend()

        Foo.objects.bulk_create([
            Foo(title='Haystack test', body='foo 1'),
            Foo(title='Another Haystack test', body='foo 2')
        ])

        Bar.objects.bulk_create([
            Bar(author='Haystack test', content='bar 1'),
            Bar(author='Another Haystack test', content='bar 2'),
            Bar(author='Yet another Haystack test', content='bar 3'),
        ])

        self.fi.reindex(using='solr')
        self.fi.reindex(using='whoosh')
        self.bi.reindex(using='solr')

    def tearDown(self):
        self.fi.clear(using='solr')
        self.bi.clear(using='solr')
        super(MultipleIndexTestCase, self).tearDown()

    def test_index_update_object_using(self):
        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 2)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        foo_3 = Foo.objects.create(
            title='Whee another Haystack test',
            body='foo 3',
        )

        self.fi.update_object(foo_3, using='solr')
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

        self.fi.remove_object(foo_1, using='solr')
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

        self.fi.clear(using='solr')
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
        self.fi.clear(using='solr')
        self.fi.clear(using='whoosh')
        self.bi.clear(using='solr')
        self.bi.clear(using='whoosh')

        results = self.solr_backend.search('foo')
        self.assertEqual(results['hits'], 0)
        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 0)

        self.fi.update(using='solr')
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
        sqs = SearchQuerySet('solr')
        self.assertEqual(sqs.count(), 5)
        self.assertEqual(sqs.models(Foo).count(), 2)
        self.assertEqual(sqs.models(Bar).count(), 3)

        self.assertEqual(sqs.using('solr').count(), 5)
        self.assertEqual(sqs.using('solr').models(Foo).count(), 2)
        self.assertEqual(sqs.using('solr').models(Bar).count(), 3)

        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Bar).count(), 0)

    def test_searchquery_using(self):
        sq = connections['solr'].get_query()

        # Using the default.
        self.assertEqual(sq.get_count(), 5)

        # "Swap" to the default.
        sq = sq.using('solr')
        self.assertEqual(sq.get_count(), 5)

        # Swap the ``SearchQuery`` used.
        sq = sq.using('whoosh')
        self.assertEqual(sq.get_count(), 2)

    def test_excluded_indexes(self):
        wui = connections['filtered_whoosh'].get_unified_index()
        self.assertEqual(len(wui.collect_indexes()), 4)
        self.assertTrue(any(isinstance(i, FooIndex) for i in wui.collect_indexes()))
        self.assertFalse(any(isinstance(i, BarIndex) for i in wui.collect_indexes()))

        # Shouldn't error.
        wui.get_index(Foo)

        # Should error, since it's not present.
        self.assertRaises(NotHandled, wui.get_index, Bar)

    def test_filtered_index_update(self):
        for i in ('whoosh', 'filtered_whoosh'):
            self.fi.clear(using=i)
            self.fi.update(using=i)

        results = self.whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 2)

        results = self.filtered_whoosh_backend.search('foo')
        self.assertEqual(results['hits'], 1, "Filtered backend should only contain one record")


class TestSignalProcessor(BaseSignalProcessor):
    def setup(self):
        self.setup_ran = True
        super(TestSignalProcessor, self).setup()

    def teardown(self):
        self.teardown_ran = True
        super(TestSignalProcessor, self).teardown()


class SignalProcessorTestCase(WhooshTestCase):
    def setUp(self):
        super(SignalProcessorTestCase, self).setUp()

        # Blatantly wrong data, just for assertion purposes.
        self.fake_connections = {}
        self.fake_router = []

        self.ui = connections['solr'].get_unified_index()
        self.fi = self.ui.get_index(Foo)
        self.bi = self.ui.get_index(Bar)
        self.solr_backend = connections['solr'].get_backend()
        self.whoosh_backend = connections['whoosh'].get_backend()

        self.foo_1 = Foo.objects.create(
            title='Haystack test',
            body='foo 1',
        )
        self.foo_2 = Foo.objects.create(
            title='Another Haystack test',
            body='foo 2',
        )
        self.bar_1 = Bar.objects.create(
            author='Haystack test',
            content='bar 1',
        )
        self.bar_2 = Bar.objects.create(
            author='Another Haystack test',
            content='bar 2',
        )
        self.bar_3 = Bar.objects.create(
            author='Yet another Haystack test',
            content='bar 3',
        )

        self.fi.reindex(using='solr')
        self.fi.reindex(using='whoosh')
        self.bi.reindex(using='solr')

    def tearDown(self):
        self.fi.clear(using='solr')
        self.bi.clear(using='solr')
        super(SignalProcessorTestCase, self).tearDown()

    def test_init(self):
        tsp = TestSignalProcessor(self.fake_connections, self.fake_router)
        self.assertEqual(tsp.connections, self.fake_connections)
        self.assertEqual(tsp.connection_router, self.fake_router)
        # We fake some side-effects to make sure it ran.
        self.assertTrue(tsp.setup_ran)

        bsp = BaseSignalProcessor(self.fake_connections, self.fake_router)
        self.assertFalse(getattr(bsp, 'setup_ran', False))

    def test_setup(self):
        tsp = TestSignalProcessor(self.fake_connections, self.fake_router)
        tsp.setup()
        self.assertTrue(tsp.setup_ran)

    def test_teardown(self):
        tsp = TestSignalProcessor(self.fake_connections, self.fake_router)
        tsp.teardown()
        self.assertTrue(tsp.teardown_ran)

    def test_handle_save(self):
        # Because the code here is pretty leaky (abstraction-wise), we'll test
        # the actual setup.
        # First, ensure the signal is setup.
        self.assertEqual(len(models.signals.post_save.receivers), 1)

        # Second, check the existing search data.
        sqs = SearchQuerySet('solr')
        self.assertEqual(sqs.using('solr').count(), 5)
        self.assertEqual(sqs.using('solr').models(Foo).count(), 2)
        self.assertEqual(sqs.using('solr').models(Bar).count(), 3)
        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)

        self.assertEqual(sqs.using('solr').models(Foo).order_by('django_id')[0].text, 'foo 1')
        self.assertEqual(sqs.using('whoosh').models(Foo).order_by('django_id')[0].text, 'foo 1')

        # Third, save the model, which should fire the signal & index the
        # new data.
        self.foo_1.body = 'A different body'
        self.foo_1.save()

        # Fourth, check the search data for the updated data, making sure counts
        # haven't changed.
        sqs = SearchQuerySet('solr')
        self.assertEqual(sqs.using('solr').count(), 5)
        self.assertEqual(sqs.using('solr').models(Foo).count(), 2)
        self.assertEqual(sqs.using('solr').models(Bar).count(), 3)
        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)

        self.assertEqual(sqs.using('solr').models(Foo).order_by('django_id')[0].text, 'A different body')
        self.assertEqual(sqs.using('whoosh').models(Foo).order_by('django_id')[0].text, 'foo 1')

    def test_handle_delete(self):
        # Because the code here is pretty leaky (abstraction-wise), we'll test
        # the actual setup.
        # First, ensure the signal is setup.
        self.assertEqual(len(models.signals.post_delete.receivers), 1)

        # Second, check the existing search data.
        sqs = SearchQuerySet('solr')
        self.assertEqual(sqs.using('solr').count(), 5)
        self.assertEqual(sqs.using('solr').models(Foo).count(), 2)
        self.assertEqual(sqs.using('solr').models(Bar).count(), 3)
        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)

        self.assertEqual(sqs.using('solr').models(Foo).order_by('django_id')[0].text, 'foo 1')
        self.assertEqual(sqs.using('whoosh').models(Foo).order_by('django_id')[0].text, 'foo 1')

        # Third, delete the model, which should fire the signal & remove the
        # record from the index.
        self.foo_1.delete()

        # Fourth, check the search data for the now-removed data, making sure counts
        # have changed correctly.
        sqs = SearchQuerySet('solr')
        self.assertEqual(sqs.using('solr').count(), 4)
        self.assertEqual(sqs.using('solr').models(Foo).count(), 1)
        self.assertEqual(sqs.using('solr').models(Bar).count(), 3)
        self.assertEqual(sqs.using('whoosh').count(), 2)
        self.assertEqual(sqs.using('whoosh').models(Foo).count(), 2)

        self.assertEqual(sqs.using('solr').models(Foo).order_by('django_id')[0].text, 'foo 2')
        self.assertEqual(sqs.using('whoosh').models(Foo).order_by('django_id')[0].text, 'foo 1')
