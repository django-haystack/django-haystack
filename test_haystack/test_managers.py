# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from django.test import TestCase
from test_haystack.core.models import MockModel

from haystack import connections
from haystack.manager import SearchIndexManager
from haystack.models import SearchResult
from haystack.query import EmptySearchQuerySet, SearchQuerySet, ValuesListSearchQuerySet, ValuesSearchQuerySet
from haystack.utils.geo import D, Point

from .mocks import CharPKMockSearchBackend
from .test_views import BasicAnotherMockModelSearchIndex, BasicMockModelSearchIndex


class CustomManager(SearchIndexManager):
    def filter(self, *args, **kwargs):
        return self.get_search_queryset().filter(content='foo1').filter(*args, **kwargs)


class CustomMockModelIndexWithObjectsManager(BasicMockModelSearchIndex):
    objects = CustomManager()


class CustomMockModelIndexWithAnotherManager(BasicMockModelSearchIndex):
    another = CustomManager()


class ManagerTestCase(TestCase):
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(ManagerTestCase, self).setUp()

        self.search_index = BasicMockModelSearchIndex
        # Update the "index".
        backend = connections['default'].get_backend()
        backend.clear()
        backend.update(self.search_index(), MockModel.objects.all())
        ui = connections['default'].get_unified_index()
        ui.build([BasicMockModelSearchIndex(), BasicAnotherMockModelSearchIndex()])

        self.search_queryset = BasicMockModelSearchIndex.objects.all()

    def test_queryset(self):
        self.assertTrue(isinstance(self.search_queryset, SearchQuerySet))

    def test_none(self):
        self.assertTrue(isinstance(self.search_index.objects.none(), EmptySearchQuerySet))

    def test_filter(self):
        sqs = self.search_index.objects.filter(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 1)

    def test_exclude(self):
        sqs = self.search_index.objects.exclude(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 1)

    def test_filter_and(self):
        sqs = self.search_index.objects.filter_and(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(sqs.query.query_filter.connector, 'AND')

    def test_filter_or(self):
        sqs = self.search_index.objects.filter_or(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(sqs.query.query_filter.connector, 'OR')

    def test_order_by(self):
        sqs = self.search_index.objects.order_by('foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue('foo' in sqs.query.order_by)

    def test_order_by_distance(self):
        p = Point(1.23, 4.56)
        sqs = self.search_index.objects.distance('location', p).order_by('distance')
        self.assertTrue(isinstance(sqs, SearchQuerySet))

        params = sqs.query.build_params()

        self.assertIn('distance_point', params)
        self.assertDictEqual(params['distance_point'], {'field': 'location',
                                                         'point': p})
        self.assertTupleEqual(params['distance_point']['point'].get_coords(), (1.23, 4.56))

        self.assertListEqual(params['sort_by'], ['distance'])

    def test_highlight(self):
        sqs = self.search_index.objects.highlight()
        self.assertEqual(sqs.query.highlight, True)

    def test_boost(self):
        sqs = self.search_index.objects.boost('foo', 10)
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.boost.keys()), 1)

    def test_facets(self):
        sqs = self.search_index.objects.facet('foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.facets), 1)

    def test_within(self):
        # This is a meaningless query but we're just confirming that the manager updates the parameters here:
        p1 = Point(-90, -90)
        p2 = Point(90, 90)
        sqs = self.search_index.objects.within('location', p1, p2)
        self.assertTrue(isinstance(sqs, SearchQuerySet))

        params = sqs.query.build_params()

        self.assertIn('within', params)
        self.assertDictEqual(params['within'], {'field': 'location', 'point_1': p1, 'point_2': p2})

    def test_dwithin(self):
        p = Point(0, 0)
        distance = D(mi=500)
        sqs = self.search_index.objects.dwithin('location', p, distance)
        self.assertTrue(isinstance(sqs, SearchQuerySet))

        params = sqs.query.build_params()

        self.assertIn('dwithin', params)
        self.assertDictEqual(params['dwithin'], {'field': 'location', 'point': p, 'distance': distance})

    def test_distance(self):
        p = Point(0, 0)
        sqs = self.search_index.objects.distance('location', p)
        self.assertTrue(isinstance(sqs, SearchQuerySet))

        params = sqs.query.build_params()
        self.assertIn('distance_point', params)
        self.assertDictEqual(params['distance_point'], {'field': 'location', 'point': p})

    def test_date_facets(self):
        sqs = self.search_index.objects.date_facet('foo',
                                                   start_date=datetime.date(2008, 2, 25),
                                                   end_date=datetime.date(2009, 2, 25),
                                                   gap_by='month')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.date_facets), 1)

    def test_query_facets(self):
        sqs = self.search_index.objects.query_facet('foo', '[bar TO *]')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_facets), 1)

    def test_narrow(self):
        sqs = self.search_index.objects.narrow("content:foo")
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertSetEqual(set(['content:foo']), sqs.query.narrow_queries)

    def test_raw_search(self):
        self.assertEqual(len(self.search_index.objects.raw_search('foo')), 23)

    def test_load_all(self):
        # Models with character primary keys.
        sqs = self.search_index.objects.all()
        sqs.query.backend = CharPKMockSearchBackend('charpk')
        results = sqs.load_all().all()
        self.assertEqual(len(results._result_cache), 0)

    def test_auto_query(self):
        sqs = self.search_index.objects.auto_query('test search -stuff')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND content__content=test search -stuff>')

        # With keyword argument
        sqs = self.search_index.objects.auto_query('test search -stuff', fieldname='title')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), "<SQ: AND title__content=test search -stuff>")

    def test_autocomplete(self):
        # Not implemented
        pass

    def test_count(self):
        self.assertEqual(SearchQuerySet().count(), 23)
        self.assertEqual(self.search_index.objects.count(), 23)

    def test_best_match(self):
        self.assertTrue(isinstance(self.search_index.objects.best_match(), SearchResult))

    def test_latest(self):
        self.assertTrue(isinstance(self.search_index.objects.latest('pub_date'), SearchResult))

    def test_more_like_this(self):
        mock = MockModel()
        mock.id = 1

        self.assertEqual(len(self.search_index.objects.more_like_this(mock)), 23)

    def test_facet_counts(self):
        self.assertEqual(self.search_index.objects.facet_counts(), {})

    def spelling_suggestion(self):
        # Test the case where spelling support is disabled.
        sqs = self.search_index.objects.filter(content='Indx')
        self.assertEqual(sqs.spelling_suggestion(), None)
        self.assertEqual(sqs.spelling_suggestion(preferred_query=None), None)

    def test_values(self):
        sqs = self.search_index.objects.auto_query("test").values("id")
        self.assert_(isinstance(sqs, ValuesSearchQuerySet))

    def test_valueslist(self):
        sqs = self.search_index.objects.auto_query("test").values_list("id")
        self.assert_(isinstance(sqs, ValuesListSearchQuerySet))


class CustomManagerTestCase(TestCase):
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(CustomManagerTestCase, self).setUp()

        self.search_index_1 = CustomMockModelIndexWithObjectsManager
        self.search_index_2 = CustomMockModelIndexWithAnotherManager

    def test_filter_object_manager(self):
        sqs = self.search_index_1.objects.filter(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)

    def test_filter_another_manager(self):
        sqs = self.search_index_2.another.filter(content='foo')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
