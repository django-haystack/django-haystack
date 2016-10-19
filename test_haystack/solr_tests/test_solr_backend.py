# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import logging as std_logging
import os
import unittest
from decimal import Decimal

import pysolr
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch

from haystack import connections, indexes, reset_search_queries
from haystack.exceptions import SkipDocument
from haystack.inputs import AltParser, AutoQuery, Raw
from haystack.models import SearchResult
from haystack.query import SQ, RelatedSearchQuerySet, SearchQuerySet
from haystack.utils.geo import Point
from haystack.utils.loading import UnifiedIndex

from ..core.models import AFourthMockModel, AnotherMockModel, ASixthMockModel, MockModel
from ..mocks import MockSearchResult

test_pickling = True

try:
    import cPickle as pickle
except ImportError:
    try:
        import pickle
    except ImportError:
        test_pickling = False


def clear_solr_index():
    # Wipe it clean.
    print('Clearing out Solr...')
    raw_solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])
    raw_solr.delete(q='*:*')


class SolrMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class SolrMockSearchIndexWithSkipDocument(SolrMockSearchIndex):

        def prepare_text(self, obj):
            if obj.author == 'daniel3':
                raise SkipDocument
            return u"Indexed!\n%s" % obj.id


class SolrMockOverriddenFieldNameSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True, index_fieldname='name_s')
    pub_date = indexes.DateField(model_attr='pub_date', index_fieldname='pub_date_dt')
    today = indexes.IntegerField(index_fieldname='today_i')

    def prepare_today(self, obj):
        return datetime.datetime.now().day

    def get_model(self):
        return MockModel


class SolrMaintainTypeMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month

    def get_model(self):
        return MockModel


class SolrMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class SolrAnotherMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return AnotherMockModel

    def prepare_text(self, obj):
        return u"You might be searching for the user %s" % obj.author


class SolrBoostMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/core/mockmodel_template.txt'
    )
    author = indexes.CharField(model_attr='author', weight=2.0)
    editor = indexes.CharField(model_attr='editor')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return AFourthMockModel


class SolrRoundTripSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, default='')
    name = indexes.CharField()
    is_active = indexes.BooleanField()
    post_count = indexes.IntegerField()
    average_rating = indexes.FloatField()
    price = indexes.DecimalField()
    pub_date = indexes.DateField()
    created = indexes.DateTimeField()
    tags = indexes.MultiValueField()
    sites = indexes.MultiValueField()

    def get_model(self):
        return MockModel

    def prepare(self, obj):
        prepped = super(SolrRoundTripSearchIndex, self).prepare(obj)
        prepped.update({
            'text': 'This is some example text.',
            'name': 'Mister Pants',
            'is_active': True,
            'post_count': 25,
            'average_rating': 3.6,
            'price': Decimal('24.99'),
            'pub_date': datetime.date(2009, 11, 21),
            'created': datetime.datetime(2009, 11, 21, 21, 31, 00),
            'tags': ['staff', 'outdoor', 'activist', 'scientist'],
            'sites': [3, 5, 1],
        })
        return prepped


class SolrComplexFacetsMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, default='')
    name = indexes.CharField(faceted=True)
    is_active = indexes.BooleanField(faceted=True)
    post_count = indexes.IntegerField()
    post_count_i = indexes.FacetIntegerField(facet_for='post_count')
    average_rating = indexes.FloatField(faceted=True)
    pub_date = indexes.DateField(faceted=True)
    created = indexes.DateTimeField(faceted=True)
    sites = indexes.MultiValueField(faceted=True)

    def get_model(self):
        return MockModel


class SolrAutocompleteMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')
    text_auto = indexes.EdgeNgramField(model_attr='foo')
    name_auto = indexes.EdgeNgramField(model_attr='author')

    def get_model(self):
        return MockModel


class SolrSpatialSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='name', document=True)
    location = indexes.LocationField()

    def prepare_location(self, obj):
        return "%s,%s" % (obj.lat, obj.lon)

    def get_model(self):
        return ASixthMockModel


class SolrQuotingMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return MockModel

    def prepare_text(self, obj):
        return u"""Don't panic but %s has been iñtërnâtiônàlizéð""" % obj.author


class SolrSearchBackendTestCase(TestCase):
    def setUp(self):
        super(SolrSearchBackendTestCase, self).setUp()

        # Wipe it clean.
        self.raw_solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.smmidni = SolrMockSearchIndexWithSkipDocument()
        self.smtmmi = SolrMaintainTypeMockSearchIndex()
        self.smofnmi = SolrMockOverriddenFieldNameSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui
        self.sb = connections['solr'].get_backend()
        self.sq = connections['solr'].get_query()

        self.sample_objs = []

        for i in range(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections['solr']._index = self.old_ui
        super(SolrSearchBackendTestCase, self).tearDown()

    def test_non_silent(self):
        bad_sb = connections['solr'].backend('bad', URL='http://omg.wtf.bbq:1000/solr', SILENTLY_FAIL=False, TIMEOUT=1)

        try:
            bad_sb.update(self.smmi, self.sample_objs)
            self.fail()
        except:
            pass

        try:
            bad_sb.remove('core.mockmodel.1')
            self.fail()
        except:
            pass

        try:
            bad_sb.clear()
            self.fail()
        except:
            pass

        try:
            bad_sb.search('foo')
            self.fail()
        except:
            pass

    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)

        results = self.raw_solr.search('*:*')
        for result in results:
            del result['_version_']
        # Check what Solr thinks is there.
        self.assertEqual(results.hits, 3)
        self.assertEqual(results.docs, [
            {
                'django_id': '1',
                'django_ct': 'core.mockmodel',
                'name': 'daniel1',
                'name_exact': 'daniel1',
                'text': 'Indexed!\n1',
                'pub_date': '2009-02-24T00:00:00Z',
                'id': 'core.mockmodel.1'
            },
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00Z',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00Z',
                'id': 'core.mockmodel.3'
            }
        ])

    def test_update_with_SkipDocument_raised(self):
        self.sb.update(self.smmidni, self.sample_objs)

        res = self.raw_solr.search('*:*')

        # Check what Solr thinks is there.
        self.assertEqual(res.hits, 2)
        self.assertListEqual(
            sorted([x['id'] for x in res.docs]),
            ['core.mockmodel.1', 'core.mockmodel.2']
        )

    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.sb.remove(self.sample_objs[0])
        results = self.raw_solr.search('*:*')
        for result in results:
            del result['_version_']
        self.assertEqual(results.hits, 2)
        self.assertEqual(results.docs, [
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00Z',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00Z',
                'id': 'core.mockmodel.3'
            }
        ])

    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.sb.clear()
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.sb.clear([AnotherMockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.sb.clear([MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)

    def test_alternate_index_fieldname(self):
        self.ui.build(indexes=[self.smofnmi])
        connections['solr']._index = self.ui
        self.sb.update(self.smofnmi, self.sample_objs)
        search = self.sb.search('*')
        self.assertEqual(search['hits'], 3)
        results = search['results']
        today = datetime.datetime.now().day
        self.assertEqual([result.today for result in results], [today, today, today])
        self.assertEqual([result.name for result in results], ['daniel1', 'daniel2', 'daniel3'])
        self.assertEqual([result.pub_date for result in results],
                         [datetime.date(2009, 2, 25) - datetime.timedelta(days=1),
                          datetime.date(2009, 2, 25) - datetime.timedelta(days=2),
                          datetime.date(2009, 2, 25) - datetime.timedelta(days=3)])
        # revert it back
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui


    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], ['1', '2', '3'])

        self.assertEqual(self.sb.search('', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('Index', highlight=True)['hits'], 3)
        self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index', highlight=True)['results']], ['<em>Indexed</em>!\n1', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n3'])

        # shortened highlighting options
        highlight_dict = {'simple.pre':'<i>', 'simple.post': '</i>'}
        self.assertEqual(self.sb.search('', highlight=highlight_dict), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('Index', highlight=highlight_dict)['hits'], 3)
        self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index', highlight=highlight_dict)['results']],
            ['<i>Indexed</i>!\n1', '<i>Indexed</i>!\n2', '<i>Indexed</i>!\n3'])

        # full-form highlighting options
        highlight_dict = {'hl.simple.pre':'<i>', 'hl.simple.post': '</i>'}
        self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index', highlight=highlight_dict)['results']],
            ['<i>Indexed</i>!\n1', '<i>Indexed</i>!\n2', '<i>Indexed</i>!\n3'])

        self.assertEqual(self.sb.search('Indx')['hits'], 0)
        self.assertEqual(self.sb.search('indax')['spelling_suggestion'], 'index')
        self.assertEqual(self.sb.search('Indx', spelling_query='indexy')['spelling_suggestion'], 'index')

        self.assertEqual(self.sb.search('', facets={'name': {}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', facets={'name': {}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['name'], [('daniel1', 1), ('daniel2', 1), ('daniel3', 1)])

        self.assertEqual(self.sb.search('', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 3, 26), 'gap_by': 'month', 'gap_amount': 1}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 3, 26), 'gap_by': 'month', 'gap_amount': 1}})
        self.assertEqual(results['hits'], 3)
        # DRL_TODO: Correct output but no counts. Another case of needing better test data?
        # self.assertEqual(results['facets']['dates']['pub_date'], {'end': '2008-02-26T00:00:00Z', 'gap': '/MONTH'})

        self.assertEqual(self.sb.search('', query_facets=[('name', '[* TO e]')]), {'hits': 0, 'results': []})
        results = self.sb.search('Index', query_facets=[('name', '[* TO e]')])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['queries'], {'name:[* TO e]': 3})

        self.assertEqual(self.sb.search('', stats={}), {'hits':0,'results':[]})
        results = self.sb.search('*:*', stats={'name':['name']})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['stats']['name']['count'], 3)

        self.assertEqual(self.sb.search('', narrow_queries=set(['name:daniel1'])), {'hits': 0, 'results': []})
        results = self.sb.search('Index', narrow_queries=set(['name:daniel1']))
        self.assertEqual(results['hits'], 1)

        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(isinstance(self.sb.search(u'index document', result_class=MockSearchResult)['results'][0], MockSearchResult))

        # Check the use of ``limit_to_registered_models``.
        self.assertEqual(self.sb.search('', limit_to_registered_models=False), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*', limit_to_registered_models=False)['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*', limit_to_registered_models=False)['results']], ['1', '2', '3'])

        # Stow.
        old_limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False

        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], ['1', '2', '3'])

        # Restore.
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = old_limit_to_registered_models

    def test_spelling(self):
        self.sb.update(self.smmi, self.sample_objs)

        self.assertEqual(self.sb.search('Indx')['hits'], 0)
        self.assertEqual(self.sb.search('indax')['spelling_suggestion'], 'index')
        self.assertEqual(self.sb.search('Indx', spelling_query='indexy')['spelling_suggestion'], 'index')

    def test_spatial_search_parameters(self):
        p1 = Point(1.23, 4.56)
        kwargs = self.sb.build_search_kwargs('*:*', distance_point={'field': 'location', 'point': p1},
                                             sort_by='distance asc')

        # Points in Solr are lat, lon pairs but Django GIS Point() uses lon, lat so we'll check for the flip
        # See https://django-haystack.readthedocs.io/en/latest/spatial.html#points
        self.assertEqual(kwargs.get('pt'), '4.56,1.23')
        self.assertEqual(kwargs.get('sfield'), 'location')
        self.assertEqual(kwargs.get('sort'), 'geodist() asc')

    def test_altparser_query(self):
        self.sb.update(self.smmi, self.sample_objs)

        results = self.sb.search(AltParser('dismax', "daniel1", qf='name', mm=1).prepare(self.sq))
        self.assertEqual(results['hits'], 1)

        # This should produce exactly the same result since all we have are mockmodel instances but we simply
        # want to confirm that using the AltParser doesn't break other options:
        results = self.sb.search(AltParser('dismax', 'daniel1', qf='name', mm=1).prepare(self.sq),
                                 narrow_queries=set(('django_ct:core.mockmodel', )))
        self.assertEqual(results['hits'], 1)

        results = self.sb.search(AltParser('dismax', '+indexed +daniel1', qf='text name', mm=1).prepare(self.sq))
        self.assertEqual(results['hits'], 1)

        self.sq.add_filter(SQ(name=AltParser('dismax', 'daniel1', qf='name', mm=1)))
        self.sq.add_filter(SQ(text='indexed'))

        new_q = self.sq._clone()
        new_q._reset()

        new_q.add_filter(SQ(name='daniel1'))
        new_q.add_filter(SQ(text=AltParser('dismax', 'indexed', qf='text')))

        results = new_q.get_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, 'core.mockmodel.1')

    def test_raw_query(self):
        self.sb.update(self.smmi, self.sample_objs)

        # Ensure that the raw bits have proper parenthesis.
        new_q = self.sq._clone()
        new_q._reset()
        new_q.add_filter(SQ(content=Raw("{!dismax qf='title^2 text' mm=1}my query")))

        results = new_q.get_results()
        self.assertEqual(len(results), 0)

    def test_altparser_quoting(self):
        test_objs = [
            MockModel(id=1, author="Foo d'Bar", pub_date=datetime.date.today()),
            MockModel(id=2, author="Baaz Quuz", pub_date=datetime.date.today()),
        ]
        self.sb.update(SolrQuotingMockSearchIndex(), test_objs)

        results = self.sb.search(AltParser('dismax', "+don't +quuz", qf='text').prepare(self.sq))
        self.assertEqual(results['hits'], 1)

    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)

        # A functional MLT example with enough data to work is below. Rely on
        # this to ensure the API is correct enough.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
        self.assertEqual([result.pk for result in self.sb.more_like_this(self.sample_objs[0])['results']], [])

    def test_build_schema(self):
        old_ui = connections['solr'].get_unified_index()

        (content_field_name, fields) = self.sb.build_schema(old_ui.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(fields), 4)
        self.assertEqual(sorted(fields, key=lambda x: x['field_name']), [
            {
                'indexed': 'true',
                'type': 'text_en',
                'stored': 'true',
                'field_name': 'name',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'field_name': 'name_exact',
                'stored': 'true',
                'type': 'string',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'date',
                'stored': 'true',
                'field_name': 'pub_date',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'text_en',
                'stored': 'true',
                'field_name': 'text',
                'multi_valued': 'false'
            },
        ])

        ui = UnifiedIndex()
        ui.build(indexes=[SolrComplexFacetsMockSearchIndex()])
        (content_field_name, fields) = self.sb.build_schema(ui.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(fields), 15)
        fields = sorted(fields, key=lambda field: field['field_name'])
        self.assertEqual(fields, [
            {
                'field_name': 'average_rating',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'float'
            },
            {
                'field_name': 'average_rating_exact',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'float'
            },
            {
                'field_name': 'created',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'date'
            },
            {
                'field_name': 'created_exact',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'date'
            },
            {
                'field_name': 'is_active',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'boolean'
            },
            {
                'field_name': 'is_active_exact',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'boolean'
            },
            {
                'field_name': 'name',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'text_en'
            },
            {
                'field_name': 'name_exact',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'string'
            },
            {
                'field_name': 'post_count',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'long'
            },
            {
                'field_name': 'post_count_i',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'long'
            },
            {
                'field_name': 'pub_date',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'date'
            },
            {
                'field_name': 'pub_date_exact',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'date'
            },
            {
                'field_name': 'sites',
                'indexed': 'true',
                'multi_valued': 'true',
                'stored': 'true',
                'type': 'text_en'
            },
            {
                'field_name': 'sites_exact',
                'indexed': 'true',
                'multi_valued': 'true',
                'stored': 'true',
                'type': 'string'
            },
            {
                'field_name': 'text',
                'indexed': 'true',
                'multi_valued': 'false',
                'stored': 'true',
                'type': 'text_en'
            }
        ])

    def test_verify_type(self):
        old_ui = connections['solr'].get_unified_index()
        ui = UnifiedIndex()
        smtmmi = SolrMaintainTypeMockSearchIndex()
        ui.build(indexes=[smtmmi])
        connections['solr']._index = ui
        sb = connections['solr'].get_backend()
        sb.update(smtmmi, self.sample_objs)

        self.assertEqual(sb.search('*:*')['hits'], 3)
        self.assertEqual([result.month for result in sb.search('*:*')['results']], [u'02', u'02', u'02'])
        connections['solr']._index = old_ui


class CaptureHandler(std_logging.Handler):
    logs_seen = []

    def emit(self, record):
        CaptureHandler.logs_seen.append(record)


@patch("pysolr.Solr._send_request", side_effect=pysolr.SolrError)
@patch("logging.Logger.log")
class FailedSolrSearchBackendTestCase(TestCase):
    def test_all_cases(self, mock_send_request, mock_log):
        self.sample_objs = []

        for i in range(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

        # Setup the rest of the bits.
        ui = UnifiedIndex()
        smmi = SolrMockSearchIndex()
        ui.build(indexes=[smmi])
        connections['solr']._index = ui
        sb = connections['solr'].get_backend()

        # Prior to the addition of the try/except bits, these would all fail miserably.
        sb.update(smmi, self.sample_objs)
        self.assertEqual(mock_log.call_count, 1)

        sb.remove(self.sample_objs[0])
        self.assertEqual(mock_log.call_count, 2)

        sb.search('search')
        self.assertEqual(mock_log.call_count, 3)

        sb.more_like_this(self.sample_objs[0])
        self.assertEqual(mock_log.call_count, 4)

        sb.clear([MockModel])
        self.assertEqual(mock_log.call_count, 5)

        sb.clear()
        self.assertEqual(mock_log.call_count, 6)


class LiveSolrSearchQueryTestCase(TestCase):
    fixtures = ['base_data.json']

    def setUp(self):
        super(LiveSolrSearchQueryTestCase, self).setUp()

        # Wipe it clean.
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui
        self.sb = connections['solr'].get_backend()
        self.sq = connections['solr'].get_query()

        # Force indexing of the content.
        self.smmi.update('solr')

    def tearDown(self):
        connections['solr']._index = self.old_ui
        super(LiveSolrSearchQueryTestCase, self).tearDown()

    def test_get_spelling(self):
        self.sq.add_filter(SQ(content='Indexy'))
        self.assertEqual(self.sq.get_spelling_suggestion(), u'(index)')
        self.assertEqual(self.sq.get_spelling_suggestion('indexy'), u'(index)')

    def test_log_query(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)

        with self.settings(DEBUG=False):
            len(self.sq.get_results())
            self.assertEqual(len(connections['solr'].queries), 0)

        with self.settings(DEBUG=True):
            # Redefine it to clear out the cached results.
            self.sq = connections['solr'].get_query()
            self.sq.add_filter(SQ(name='bar'))
            len(self.sq.get_results())
            self.assertEqual(len(connections['solr'].queries), 1)
            self.assertEqual(connections['solr'].queries[0]['query_string'], 'name:(bar)')

            # And again, for good measure.
            self.sq = connections['solr'].get_query()
            self.sq.add_filter(SQ(name='bar'))
            self.sq.add_filter(SQ(text='moof'))
            len(self.sq.get_results())
            self.assertEqual(len(connections['solr'].queries), 2)
            self.assertEqual(connections['solr'].queries[0]['query_string'], 'name:(bar)')
            self.assertEqual(connections['solr'].queries[1]['query_string'], u'(name:(bar) AND text:(moof))')


@override_settings(DEBUG=True)
class LiveSolrSearchQuerySetTestCase(TestCase):
    """Used to test actual implementation details of the SearchQuerySet."""
    fixtures = ['base_data.json', 'bulk_data.json']

    @classmethod
    def setUpClass(cls):
        super(LiveSolrSearchQuerySetTestCase, cls).setUpClass()
        cls._index_updated = False

    @classmethod
    def tearDownClass(cls):
        del cls._index_updated
        super(LiveSolrSearchQuerySetTestCase, cls).tearDownClass()

    def setUp(self):
        super(LiveSolrSearchQuerySetTestCase, self).setUp()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui

        self.sqs = SearchQuerySet('solr')
        self.rsqs = RelatedSearchQuerySet('solr')

        if not self._index_updated:
            std_logging.info('Reindexing test data')

            # Wipe it clean.
            clear_solr_index()

            # Force indexing of the content.
            self.smmi.update('solr')

            self._index_updated = True

    def tearDown(self):
        # Restore.
        connections['solr']._index = self.old_ui
        super(LiveSolrSearchQuerySetTestCase, self).tearDown()

    def test_load_all(self):
        sqs = self.sqs.load_all()
        self.assertTrue(len(sqs) > 0)
        # load_all should not change the results or their ordering:
        self.assertListEqual([i.id for i in sqs], [i.id for i in self.sqs])
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.maxDiff = None
        self.assertEqual(sqs[0].object.foo, u"Registering indexes in Haystack is very similar to registering models and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to override the default indexing behavior for your model you can specify your own ``SearchIndex`` class.  This is useful for ensuring that future-dated or non-live content is not indexed and searchable. Our ``Note`` model has a ``pub_date`` field, so let's update our code to include our own ``SearchIndex`` to exclude indexing future-dated notes:")

    def test_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        sqs = self.sqs.all()
        results = [int(result.pk) for result in iter(sqs)]
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections['solr'].queries), 3)

    def test_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.sqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(len(connections['solr'].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.sqs.all()
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(connections['solr'].queries), 1)

    def test_values_list_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)

        # TODO: this would be a good candidate for refactoring into a TestCase subclass shared across backends

        # The values will come back as strings because Hasytack doesn't assume PKs are integers.
        # We'll prepare this set once since we're going to query the same results in multiple ways:
        expected_pks = [str(i) for i in [3, 2, 4, 5, 6, 7, 8, 9, 10, 11]]

        results = self.sqs.all().order_by('pub_date').values('pk')
        self.assertListEqual([i['pk'] for i in results[1:11]], expected_pks)

        results = self.sqs.all().order_by('pub_date').values_list('pk')
        self.assertListEqual([i[0] for i in results[1:11]], expected_pks)

        results = self.sqs.all().order_by('pub_date').values_list('pk', flat=True)
        self.assertListEqual(results[1:11], expected_pks)

        self.assertEqual(len(connections['solr'].queries), 3)

    def test_count(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        sqs = self.sqs.all()
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(len(sqs), 23)
        self.assertEqual(sqs.count(), 23)
        # Should only execute one query to count the length of the result set.
        self.assertEqual(len(connections['solr'].queries), 1)

    def test_manual_iter(self):
        results = self.sqs.all()

        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections['solr'].queries), 3)

    def test_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.sqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections['solr'].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(connections['solr'].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(connections['solr'].queries), 2)

    def test_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        self.assertEqual(self.sqs._cache_is_full(), False)
        results = self.sqs.all()
        fire_the_iterator_and_fill_cache = list(results)
        self.assertEqual(23, len(fire_the_iterator_and_fill_cache))
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections['solr'].queries), 4)

    def test___and__(self):
        sqs1 = self.sqs.filter(content='foo')
        sqs2 = self.sqs.filter(content='bar')
        sqs = sqs1 & sqs2

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'((foo) AND (bar))')

        # Now for something more complex...
        sqs3 = self.sqs.exclude(title='moof').filter(SQ(content='foo') | SQ(content='baz'))
        sqs4 = self.sqs.filter(content='bar')
        sqs = sqs3 & sqs4

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 3)
        self.assertEqual(sqs.query.build_query(), u'(NOT (title:(moof)) AND ((foo) OR (baz)) AND (bar))')

    def test___or__(self):
        sqs1 = self.sqs.filter(content='foo')
        sqs2 = self.sqs.filter(content='bar')
        sqs = sqs1 | sqs2

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'((foo) OR (bar))')

        # Now for something more complex...
        sqs3 = self.sqs.exclude(title='moof').filter(SQ(content='foo') | SQ(content='baz'))
        sqs4 = self.sqs.filter(content='bar').models(MockModel)
        sqs = sqs3 | sqs4

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'((NOT (title:(moof)) AND ((foo) OR (baz))) OR (bar))')

    def test_auto_query(self):
        # Ensure bits in exact matches get escaped properly as well.
        # This will break horrifically if escaping isn't working.
        sqs = self.sqs.auto_query('"pants:rule"')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND content__content="pants:rule">')
        self.assertEqual(sqs.query.build_query(), u'("pants\\:rule")')
        self.assertEqual(len(sqs), 0)

        sqs = self.sqs.auto_query('Canon+PowerShot+ELPH+(Black)')
        self.assertEqual(sqs.query.build_query(), u'Canon\\+PowerShot\\+ELPH\\+\\(Black\\)')
        sqs = sqs.filter(tags__in=['cameras', 'electronics'])
        self.assertEqual(len(sqs), 0)

    def test_query__in(self):
        self.assertGreater(len(self.sqs), 0)
        sqs = self.sqs.filter(django_ct='core.mockmodel', django_id__in=[1,2])
        self.assertEqual(len(sqs), 2)

    def test_query__in_empty_list(self):
        """Confirm that an empty list avoids a Solr exception"""
        self.assertGreater(len(self.sqs), 0)
        sqs = self.sqs.filter(id__in=[])
        self.assertEqual(len(sqs), 0)

    # Regressions

    def test_regression_proper_start_offsets(self):
        sqs = self.sqs.filter(text='index')
        self.assertNotEqual(sqs.count(), 0)

        id_counts = {}

        for item in sqs:
            if item.id in id_counts:
                id_counts[item.id] += 1
            else:
                id_counts[item.id] = 1

        for key, value in id_counts.items():
            if value > 1:
                self.fail("Result with id '%s' seen more than once in the results." % key)

    def test_regression_raw_search_breaks_slicing(self):
        sqs = self.sqs.raw_search('text: index')
        page_1 = [result.pk for result in sqs[0:10]]
        page_2 = [result.pk for result in sqs[10:20]]

        for pk in page_2:
            if pk in page_1:
                self.fail("Result with id '%s' seen more than once in the results." % pk)

    # RelatedSearchQuerySet Tests

    def test_related_load_all(self):
        sqs = self.rsqs.load_all()

        # load_all should not change the results or their ordering:
        self.assertListEqual([i.id for i in sqs], [i.id for i in self.rsqs])

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue(len(sqs) > 0)

        self.assertEqual(sqs[0].object.foo, u"Registering indexes in Haystack is very similar to registering models and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to override the default indexing behavior for your model you can specify your own ``SearchIndex`` class.  This is useful for ensuring that future-dated or non-live content is not indexed and searchable. Our ``Note`` model has a ``pub_date`` field, so let's update our code to include our own ``SearchIndex`` to exclude indexing future-dated notes:")

    def test_related_load_all_queryset(self):
        sqs = self.rsqs.load_all()

        # load_all should not change the results or their ordering:
        self.assertListEqual([i.id for i in sqs], [i.id for i in self.rsqs])

        self.assertEqual(len(sqs._load_all_querysets), 0)

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], list(range(2, 24)))

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=10))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], list(range(11, 24)))
        self.assertEqual([obj.object.id for obj in sqs[10:20]], [21, 22, 23])

    def test_related_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        sqs = self.rsqs.all()
        results = [int(result.pk) for result in iter(sqs)]
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections['solr'].queries), 3)

    def test_related_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(len(connections['solr'].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(connections['solr'].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[20:30]], [21, 22, 23])
        self.assertEqual(len(connections['solr'].queries), 1)

    def test_related_manual_iter(self):
        results = self.rsqs.all()
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections['solr'].queries), 3)

    def test_related_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections['solr'].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(connections['solr'].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(connections['solr'].queries), 2)

    def test_related_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections['solr'].queries), 0)
        self.assertEqual(self.rsqs._cache_is_full(), False)
        results = self.rsqs.all()
        fire_the_iterator_and_fill_cache = list(results)
        self.assertEqual(23, len(fire_the_iterator_and_fill_cache))
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections['solr'].queries), 4)

    def test_quotes_regression(self):
        sqs = self.sqs.auto_query(u"44°48'40''N 20°28'32''E")
        # Should not have empty terms.
        self.assertEqual(sqs.query.build_query(), u"(44\xb048'40''N 20\xb028'32''E)")
        # Should not cause Solr to 500.
        try:
            sqs.count()
        except Exception as exc:
            self.fail("raised unexpected error: %s" % exc)

        sqs = self.sqs.auto_query('blazing')
        self.assertEqual(sqs.query.build_query(), u'(blazing)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('blazing saddles')
        self.assertEqual(sqs.query.build_query(), u'(blazing saddles)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles')
        self.assertEqual(sqs.query.build_query(), u'(\\"blazing saddles)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles"')
        self.assertEqual(sqs.query.build_query(), u'("blazing saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles"')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing \'saddles"')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing \'saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing \'\'saddles"')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing \'\'saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing \'\'saddles"\'')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing \'\'saddles" \')')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing \'\'saddles"\'"')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing \'\'saddles" \'\\")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles" mel')
        self.assertEqual(sqs.query.build_query(), u'("blazing saddles" mel)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles" mel brooks')
        self.assertEqual(sqs.query.build_query(), u'("blazing saddles" mel brooks)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles" brooks')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing saddles" brooks)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles" "brooks')
        self.assertEqual(sqs.query.build_query(), u'(mel "blazing saddles" \\"brooks)')
        self.assertEqual(sqs.count(), 0)

    def test_query_generation(self):
        sqs = self.sqs.filter(SQ(content=AutoQuery("hello world")) | SQ(title=AutoQuery("hello world")))
        self.assertEqual(sqs.query.build_query(), u"((hello world) OR title:(hello world))")

    def test_result_class(self):
        # Assert that we're defaulting to ``SearchResult``.
        sqs = self.sqs.all()
        self.assertTrue(isinstance(sqs[0], SearchResult))

        # Custom class.
        sqs = self.sqs.result_class(MockSearchResult).all()
        self.assertTrue(isinstance(sqs[0], MockSearchResult))

        # Reset to solr.
        sqs = self.sqs.result_class(None).all()
        self.assertTrue(isinstance(sqs[0], SearchResult))


class LiveSolrMoreLikeThisTestCase(TestCase):
    fixtures = ['base_data.json', 'bulk_data.json']

    def setUp(self):
        super(LiveSolrMoreLikeThisTestCase, self).setUp()

        # Wipe it clean.
        clear_solr_index()

        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockModelSearchIndex()
        self.sammi = SolrAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi, self.sammi])
        connections['solr']._index = self.ui

        self.sqs = SearchQuerySet('solr')

        self.smmi.update('solr')
        self.sammi.update('solr')

    def tearDown(self):
        # Restore.
        connections['solr']._index = self.old_ui
        super(LiveSolrMoreLikeThisTestCase, self).tearDown()

    def test_more_like_this(self):
        all_mlt = self.sqs.more_like_this(MockModel.objects.get(pk=1))
        self.assertEqual(all_mlt.count(), len([result.pk for result in all_mlt]),
                         msg="mlt SearchQuerySet .count() didn't match retrieved result length")

        # Rather than hard-code assumptions about Solr's return order, we have a few very similar
        # items which we'll confirm are included in the first 5 results. This is still ugly as we're
        # hard-coding primary keys but it's better than breaking any time a Solr update or data
        # change causes a score to shift slightly

        top_results = [int(result.pk) for result in all_mlt[:5]]
        for i in (14, 6, 4, 22, 10):
            self.assertIn(i, top_results)

        filtered_mlt = self.sqs.filter(name='daniel3').more_like_this(MockModel.objects.get(pk=3))
        self.assertLess(filtered_mlt.count(), all_mlt.count())
        top_filtered_results = [int(result.pk) for result in filtered_mlt[:5]]

        for i in (16, 17, 19, 22, 23):
            self.assertIn(i, top_filtered_results)

        filtered_mlt_with_models = self.sqs.models(MockModel).more_like_this(MockModel.objects.get(pk=1))
        self.assertLessEqual(filtered_mlt_with_models.count(), all_mlt.count())
        top_filtered_with_models = [int(result.pk) for result in filtered_mlt_with_models[:5]]
        for i in (14, 6, 4, 22, 10):
            self.assertIn(i, top_filtered_with_models)

    def test_more_like_this_defer(self):
        mi = MockModel.objects.defer('foo').get(pk=1)
        deferred = self.sqs.models(MockModel).more_like_this(mi)
        top_results = [int(result.pk) for result in deferred[:5]]
        for i in (14, 6, 4, 22, 10):
            self.assertIn(i, top_results)

    def test_more_like_this_custom_result_class(self):
        """Ensure that swapping the ``result_class`` works"""
        first_result = self.sqs.result_class(MockSearchResult).more_like_this(MockModel.objects.get(pk=1))[0]
        self.assertIsInstance(first_result, MockSearchResult)


class LiveSolrAutocompleteTestCase(TestCase):
    fixtures = ['base_data.json', 'bulk_data.json']

    def setUp(self):
        super(LiveSolrAutocompleteTestCase, self).setUp()

        # Wipe it clean.
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrAutocompleteMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui

        self.sqs = SearchQuerySet('solr')

        self.smmi.update(using='solr')

    def tearDown(self):
        # Restore.
        connections['solr']._index = self.old_ui
        super(LiveSolrAutocompleteTestCase, self).tearDown()

    def test_autocomplete(self):
        autocomplete = self.sqs.autocomplete(text_auto='mod')
        self.assertEqual(autocomplete.count(), 5)
        self.assertEqual([result.pk for result in autocomplete], ['1', '12', '6', '7', '14'])
        self.assertTrue('mod' in autocomplete[0].text.lower())
        self.assertTrue('mod' in autocomplete[1].text.lower())
        self.assertTrue('mod' in autocomplete[2].text.lower())
        self.assertTrue('mod' in autocomplete[3].text.lower())
        self.assertTrue('mod' in autocomplete[4].text.lower())
        self.assertEqual(len([result.pk for result in autocomplete]), 5)

        # Test multiple words.
        autocomplete_2 = self.sqs.autocomplete(text_auto='your mod')
        self.assertEqual(autocomplete_2.count(), 3)
        self.assertEqual([result.pk for result in autocomplete_2], ['1', '14', '6'])
        self.assertTrue('your' in autocomplete_2[0].text.lower())
        self.assertTrue('mod' in autocomplete_2[0].text.lower())
        self.assertTrue('your' in autocomplete_2[1].text.lower())
        self.assertTrue('mod' in autocomplete_2[1].text.lower())
        self.assertTrue('your' in autocomplete_2[2].text.lower())
        self.assertTrue('mod' in autocomplete_2[2].text.lower())
        self.assertEqual(len([result.pk for result in autocomplete_2]), 3)

        # Test multiple fields.
        autocomplete_3 = self.sqs.autocomplete(text_auto='Django', name_auto='dan')
        self.assertEqual(autocomplete_3.count(), 4)
        self.assertEqual([result.pk for result in autocomplete_3], ['12', '1', '14', '22'])
        self.assertEqual(len([result.pk for result in autocomplete_3]), 4)


class LiveSolrRoundTripTestCase(TestCase):
    def setUp(self):
        super(LiveSolrRoundTripTestCase, self).setUp()

        # Wipe it clean.
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.srtsi = SolrRoundTripSearchIndex()
        self.ui.build(indexes=[self.srtsi])
        connections['solr']._index = self.ui
        self.sb = connections['solr'].get_backend()

        self.sqs = SearchQuerySet('solr')

        # Fake indexing.
        mock = MockModel()
        mock.id = 1
        self.sb.update(self.srtsi, [mock])

    def tearDown(self):
        # Restore.
        connections['solr']._index = self.old_ui
        super(LiveSolrRoundTripTestCase, self).tearDown()

    def test_round_trip(self):
        results = self.sqs.filter(id='core.mockmodel.1')

        # Sanity check.
        self.assertEqual(results.count(), 1)

        # Check the individual fields.
        result = results[0]
        self.assertEqual(result.id, 'core.mockmodel.1')
        self.assertEqual(result.text, 'This is some example text.')
        self.assertEqual(result.name, 'Mister Pants')
        self.assertEqual(result.is_active, True)
        self.assertEqual(result.post_count, 25)
        self.assertEqual(result.average_rating, 3.6)
        self.assertEqual(result.price, u'24.99')
        self.assertEqual(result.pub_date, datetime.date(2009, 11, 21))
        self.assertEqual(result.created, datetime.datetime(2009, 11, 21, 21, 31, 00))
        self.assertEqual(result.tags, ['staff', 'outdoor', 'activist', 'scientist'])
        self.assertEqual(result.sites, [3, 5, 1])


@unittest.skipUnless(test_pickling, 'Skipping pickling tests')
class LiveSolrPickleTestCase(TestCase):
    fixtures = ['base_data.json', 'bulk_data.json']

    def setUp(self):
        super(LiveSolrPickleTestCase, self).setUp()

        # Wipe it clean.
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrMockModelSearchIndex()
        self.sammi = SolrAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi, self.sammi])
        connections['solr']._index = self.ui

        self.sqs = SearchQuerySet('solr')

        self.smmi.update('solr')
        self.sammi.update('solr')

    def tearDown(self):
        # Restore.
        connections['solr']._index = self.old_ui
        super(LiveSolrPickleTestCase, self).tearDown()

    def test_pickling(self):
        results = self.sqs.all()

        for res in results:
            # Make sure the cache is full.
            pass

        in_a_pickle = pickle.dumps(results)
        like_a_cuke = pickle.loads(in_a_pickle)
        self.assertEqual(len(like_a_cuke), len(results))
        self.assertEqual(like_a_cuke[0].id, results[0].id)


class SolrBoostBackendTestCase(TestCase):
    def setUp(self):
        super(SolrBoostBackendTestCase, self).setUp()

        # Wipe it clean.
        self.raw_solr = pysolr.Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])
        clear_solr_index()

        # Stow.
        self.old_ui = connections['solr'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = SolrBoostMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['solr']._index = self.ui
        self.sb = connections['solr'].get_backend()

        self.sample_objs = []

        for i in range(1, 5):
            mock = AFourthMockModel()
            mock.id = i

            if i % 2:
                mock.author = 'daniel'
                mock.editor = 'david'
            else:
                mock.author = 'david'
                mock.editor = 'daniel'

            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections['solr']._index = self.old_ui
        super(SolrBoostBackendTestCase, self).tearDown()

    def test_boost(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 4)

        results = SearchQuerySet('solr').filter(SQ(author='daniel') | SQ(editor='daniel'))

        self.assertEqual([result.id for result in results], [
            'core.afourthmockmodel.1',
            'core.afourthmockmodel.3',
            'core.afourthmockmodel.2',
            'core.afourthmockmodel.4'
        ])


@unittest.skipIf(pysolr.__version__ < (3, 1, 1), 'content extraction requires pysolr > 3.1.0')
class LiveSolrContentExtractionTestCase(TestCase):
    def setUp(self):
        super(LiveSolrContentExtractionTestCase, self).setUp()

        self.sb = connections['solr'].get_backend()

    def test_content_extraction(self):
        f = open(os.path.join(os.path.dirname(__file__),
                              "content_extraction", "test.pdf"),
                 "rb")

        data = self.sb.extract_file_contents(f)

        self.assertTrue("haystack" in data['contents'])
        self.assertEqual(data['metadata']['Content-Type'], [u'application/pdf'])
        self.assertTrue(any(i for i in data['metadata']['Keywords'] if 'SolrCell' in i))
