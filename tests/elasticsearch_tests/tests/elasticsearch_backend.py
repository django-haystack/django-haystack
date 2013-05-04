# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
import logging as std_logging

import pyelasticsearch
import requests
from django.conf import settings
from django.test import TestCase
from django.utils import unittest
from haystack import connections, reset_search_queries
from haystack import indexes
from haystack.inputs import AutoQuery
from haystack.models import SearchResult
from haystack.query import SearchQuerySet, RelatedSearchQuerySet, SQ
from haystack.utils import log as logging
from haystack.utils.loading import UnifiedIndex
from core.models import (MockModel, AnotherMockModel,
                         AFourthMockModel, ASixthMockModel)
from core.tests.mocks import MockSearchResult

test_pickling = True

try:
    import cPickle as pickle
except ImportError:
    try:
        import pickle
    except ImportError:
        test_pickling = False


def clear_elasticsearch_index():
    # Wipe it clean.
    raw_es = pyelasticsearch.ElasticSearch(settings.HAYSTACK_CONNECTIONS['default']['URL'])
    try:
        raw_es.delete_index(settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME'])
        raw_es.refresh()
    except (requests.RequestException, pyelasticsearch.ElasticHttpError):
        pass


class ElasticsearchMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class ElasticsearchMaintainTypeMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateField(model_attr='pub_date')

    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month

    def get_model(self):
        return MockModel


class ElasticsearchMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class ElasticsearchAnotherMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return AnotherMockModel

    def prepare_text(self, obj):
        return u"You might be searching for the user %s" % obj.author


class ElasticsearchBoostMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/core/mockmodel_template.txt'
    )
    author = indexes.CharField(model_attr='author', weight=2.0)
    editor = indexes.CharField(model_attr='editor')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return AFourthMockModel


class ElasticsearchRoundTripSearchIndex(indexes.SearchIndex, indexes.Indexable):
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
        prepped = super(ElasticsearchRoundTripSearchIndex, self).prepare(obj)
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


class ElasticsearchComplexFacetsMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
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


class ElasticsearchAutocompleteMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')
    text_auto = indexes.EdgeNgramField(model_attr='foo')
    name_auto = indexes.EdgeNgramField(model_attr='author')

    def get_model(self):
        return MockModel


class ElasticsearchSpatialSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='name', document=True)
    location = indexes.LocationField()

    def prepare_location(self, obj):
        return "%s,%s" % (obj.lat, obj.lon)

    def get_model(self):
        return ASixthMockModel


class ElasticsearchSearchBackendTestCase(TestCase):
    def setUp(self):
        super(ElasticsearchSearchBackendTestCase, self).setUp()

        # Wipe it clean.
        self.raw_es = pyelasticsearch.ElasticSearch(settings.HAYSTACK_CONNECTIONS['default']['URL'])
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchMockSearchIndex()
        self.smtmmi = ElasticsearchMaintainTypeMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui
        self.sb = connections['default'].get_backend()

        # Force the backend to rebuild the mapping each time.
        self.sb.existing_mapping = {}
        self.sb.setup()

        self.sample_objs = []

        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections['default']._index = self.old_ui
        super(ElasticsearchSearchBackendTestCase, self).tearDown()

    def raw_search(self, query):
        try:
            return self.raw_es.search('*:*', index=settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME'])
        except (requests.RequestException, pyelasticsearch.ElasticHttpError):
            return {}

    def test_non_silent(self):
        bad_sb = connections['default'].backend('bad', URL='http://omg.wtf.bbq:1000/', INDEX_NAME='whatver', SILENTLY_FAIL=False, TIMEOUT=1)

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

        # Check what Elasticsearch thinks is there.
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 3)
        self.assertEqual(sorted([res['_source'] for res in self.raw_search('*:*')['hits']['hits']], cmp=lambda x, y: cmp(x['id'], y['id'])), [
            {
                'django_id': '1',
                'django_ct': 'core.mockmodel',
                'name': 'daniel1',
                'name_exact': 'daniel1',
                'text': 'Indexed!\n1',
                'pub_date': '2009-02-24T00:00:00',
                'id': 'core.mockmodel.1'
            },
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00',
                'id': 'core.mockmodel.3'
            }
        ])

    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 3)

        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 2)
        self.assertEqual([res['_source'] for res in self.raw_search('*:*')['hits']['hits']], [
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00',
                'id': 'core.mockmodel.3'
            }
        ])

    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 3)

        self.sb.clear()
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 3)

        self.sb.clear([AnotherMockModel])
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 3)

        self.sb.clear([MockModel])
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 3)

        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(self.raw_search('*:*').get('hits', {}).get('total', 0), 0)

    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 3)

        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], [u'2', u'1', u'3'])

        self.assertEqual(self.sb.search('', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('Index', highlight=True)['hits'], 3)
        self.assertEqual([result.highlighted for result in self.sb.search('Index', highlight=True)['results']],
            [[u'<em>Indexed</em>!\n2'], [u'<em>Indexed</em>!\n1'], [u'<em>Indexed</em>!\n3']])

        self.assertEqual(self.sb.search('Indx')['hits'], 0)
        self.assertEqual(self.sb.search('indaxed')['spelling_suggestion'], 'indexed')
        self.assertEqual(self.sb.search('arf', spelling_query='indexyd')['spelling_suggestion'], 'indexed')

        self.assertEqual(self.sb.search('', facets={'name': {}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', facets={'name': {}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['name'], [('daniel3', 1), ('daniel2', 1), ('daniel1', 1)])

        self.assertEqual(self.sb.search('', date_facets={'pub_date': {'start_date': datetime.date(2008, 1, 1), 'end_date': datetime.date(2009, 4, 1), 'gap_by': 'month', 'gap_amount': 1}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', date_facets={'pub_date': {'start_date': datetime.date(2008, 1, 1), 'end_date': datetime.date(2009, 4, 1), 'gap_by': 'month', 'gap_amount': 1}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['dates']['pub_date'], [(datetime.datetime(2009, 2, 1, 0, 0), 3)])

        self.assertEqual(self.sb.search('', query_facets=[('name', '[* TO e]')]), {'hits': 0, 'results': []})
        results = self.sb.search('Index', query_facets=[('name', '[* TO e]')])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['queries'], {u'name': 3})

        self.assertEqual(self.sb.search('', narrow_queries=set(['name:daniel1'])), {'hits': 0, 'results': []})
        results = self.sb.search('Index', narrow_queries=set(['name:daniel1']))
        self.assertEqual(results['hits'], 1)

        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(isinstance(self.sb.search(u'index', result_class=MockSearchResult)['results'][0], MockSearchResult))

        # Check the use of ``limit_to_registered_models``.
        self.assertEqual(self.sb.search('', limit_to_registered_models=False), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*', limit_to_registered_models=False)['hits'], 3)
        self.assertEqual(sorted([result.pk for result in self.sb.search('*:*', limit_to_registered_models=False)['results']]), ['1', '2', '3'])

        # Stow.
        old_limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False

        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual(sorted([result.pk for result in self.sb.search('*:*')['results']]), ['1', '2', '3'])

        # Restore.
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = old_limit_to_registered_models

    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 3)

        # A functional MLT example with enough data to work is below. Rely on
        # this to ensure the API is correct enough.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
        self.assertEqual([result.pk for result in self.sb.more_like_this(self.sample_objs[0])['results']], [])

    def test_build_schema(self):
        old_ui = connections['default'].get_unified_index()

        (content_field_name, mapping) = self.sb.build_schema(old_ui.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(mapping), 4)
        self.assertEqual(mapping, {
            'text': {'index': 'analyzed', 'term_vector': 'with_positions_offsets', 'type': 'string', 'analyzer': 'snowball', 'boost': 1.0, 'store': 'yes'},
            'pub_date': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'date'},
            'name': {'index': 'analyzed', 'term_vector': 'with_positions_offsets', 'type': 'string', 'analyzer': 'snowball', 'boost': 1.0, 'store': 'yes'},
            'name_exact': {'index': 'not_analyzed', 'term_vector': 'with_positions_offsets', 'boost': 1.0, 'store': 'yes', 'type': 'string'}
        })

        ui = UnifiedIndex()
        ui.build(indexes=[ElasticsearchComplexFacetsMockSearchIndex()])
        (content_field_name, mapping) = self.sb.build_schema(ui.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(mapping), 15)
        self.assertEqual(mapping, {
            'name': {'index': 'analyzed', 'term_vector': 'with_positions_offsets', 'type': 'string', 'analyzer': 'snowball', 'boost': 1.0, 'store': 'yes'},
            'is_active_exact': {'index': 'not_analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'boolean'},
            'created': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'date'},
            'post_count': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'long'},
            'created_exact': {'index': 'not_analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'date'},
            'sites_exact': {'index': 'not_analyzed', 'term_vector': 'with_positions_offsets', 'boost': 1.0, 'store': 'yes', 'type': 'string'},
            'is_active': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'boolean'},
            'sites': {'index': 'analyzed', 'term_vector': 'with_positions_offsets', 'type': 'string', 'analyzer': 'snowball', 'boost': 1.0, 'store': 'yes'},
            'post_count_i': {'index': 'not_analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'long'},
            'average_rating': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'float'},
            'text': {'index': 'analyzed', 'term_vector': 'with_positions_offsets', 'type': 'string', 'analyzer': 'snowball', 'boost': 1.0, 'store': 'yes'},
            'pub_date_exact': {'index': 'not_analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'date'},
            'name_exact': {'index': 'not_analyzed', 'term_vector': 'with_positions_offsets', 'boost': 1.0, 'store': 'yes', 'type': 'string'},
            'pub_date': {'index': 'analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'date'},
            'average_rating_exact': {'index': 'not_analyzed', 'boost': 1.0, 'store': 'yes', 'type': 'float'}
        })

    def test_verify_type(self):
        old_ui = connections['default'].get_unified_index()
        ui = UnifiedIndex()
        smtmmi = ElasticsearchMaintainTypeMockSearchIndex()
        ui.build(indexes=[smtmmi])
        connections['default']._index = ui
        sb = connections['default'].get_backend()
        sb.update(smtmmi, self.sample_objs)

        self.assertEqual(sb.search('*:*')['hits'], 3)
        self.assertEqual([result.month for result in sb.search('*:*')['results']], [u'02', u'02', u'02'])
        connections['default']._index = old_ui


class CaptureHandler(std_logging.Handler):
    logs_seen = []

    def emit(self, record):
        CaptureHandler.logs_seen.append(record)


class FailedElasticsearchSearchBackendTestCase(TestCase):
    def setUp(self):
        self.sample_objs = []

        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

        # Stow.
        # Point the backend at a URL that doesn't exist so we can watch the
        # sparks fly.
        self.old_es_url = settings.HAYSTACK_CONNECTIONS['default']['URL']
        settings.HAYSTACK_CONNECTIONS['default']['URL'] = "%s/foo/" % self.old_es_url
        self.cap = CaptureHandler()
        logging.getLogger('haystack').addHandler(self.cap)
        import haystack
        logging.getLogger('haystack').removeHandler(haystack.stream)

        # Setup the rest of the bits.
        self.old_ui = connections['default'].get_unified_index()
        ui = UnifiedIndex()
        self.smmi = ElasticsearchMockSearchIndex()
        ui.build(indexes=[self.smmi])
        connections['default']._index = ui
        self.sb = connections['default'].get_backend()

    def tearDown(self):
        import haystack
        # Restore.
        settings.HAYSTACK_CONNECTIONS['default']['URL'] = self.old_es_url
        connections['default']._index = self.old_ui
        logging.getLogger('haystack').removeHandler(self.cap)
        logging.getLogger('haystack').addHandler(haystack.stream)

    @unittest.expectedFailure
    def test_all_cases(self):
        # Prior to the addition of the try/except bits, these would all fail miserably.
        self.assertEqual(len(CaptureHandler.logs_seen), 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(CaptureHandler.logs_seen), 1)

        self.sb.remove(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 2)

        self.sb.search('search')
        self.assertEqual(len(CaptureHandler.logs_seen), 3)

        self.sb.more_like_this(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 4)

        self.sb.clear([MockModel])
        self.assertEqual(len(CaptureHandler.logs_seen), 5)

        self.sb.clear()
        self.assertEqual(len(CaptureHandler.logs_seen), 6)


class LiveElasticsearchSearchQueryTestCase(TestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        super(LiveElasticsearchSearchQueryTestCase, self).setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui
        self.sb = connections['default'].get_backend()
        self.sq = connections['default'].get_query()

        # Force indexing of the content.
        self.smmi.update()

    def tearDown(self):
        connections['default']._index = self.old_ui
        super(LiveElasticsearchSearchQueryTestCase, self).tearDown()

    def test_log_query(self):
        from django.conf import settings
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)

        # Stow.
        old_debug = settings.DEBUG
        settings.DEBUG = False

        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 0)

        settings.DEBUG = True
        # Redefine it to clear out the cached results.
        self.sq = connections['default'].query()
        self.sq.add_filter(SQ(name='bar'))
        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 1)
        self.assertEqual(connections['default'].queries[0]['query_string'], 'name:(bar)')

        # And again, for good measure.
        self.sq = connections['default'].query()
        self.sq.add_filter(SQ(name='bar'))
        self.sq.add_filter(SQ(text='moof'))
        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 2)
        self.assertEqual(connections['default'].queries[0]['query_string'], 'name:(bar)')
        self.assertEqual(connections['default'].queries[1]['query_string'], u'(name:(bar) AND text:(moof))')

        # Restore.
        settings.DEBUG = old_debug


lssqstc_all_loaded = None


class LiveElasticsearchSearchQuerySetTestCase(TestCase):
    """Used to test actual implementation details of the SearchQuerySet."""
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(LiveElasticsearchSearchQuerySetTestCase, self).setUp()

        # Stow.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui

        self.sqs = SearchQuerySet()
        self.rsqs = RelatedSearchQuerySet()

        # Ugly but not constantly reindexing saves us almost 50% runtime.
        global lssqstc_all_loaded

        if lssqstc_all_loaded is None:
            lssqstc_all_loaded = True

            # Wipe it clean.
            clear_elasticsearch_index()

            # Force indexing of the content.
            self.smmi.update()

    def tearDown(self):
        # Restore.
        connections['default']._index = self.old_ui
        settings.DEBUG = self.old_debug
        super(LiveElasticsearchSearchQuerySetTestCase, self).tearDown()

    def test_load_all(self):
        sqs = self.sqs.load_all()
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue(len(sqs) > 0)
        self.assertEqual(sqs[0].object.foo, u'In addition, you may specify other fields to be populated along with the document. In this case, we also index the user who authored the document as well as the date the document was published. The variable you assign the SearchField to should directly map to the field your search backend is expecting. You instantiate most search fields with a parameter that points to the attribute of the object to populate that field with.')

    def test_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        sqs = self.sqs.all()
        results = sorted([int(result.pk) for result in sqs])
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(connections['default'].queries), 3)

    def test_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.sqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [7, 12, 17, 1, 6, 11, 16, 23, 5, 10])
        self.assertEqual(len(connections['default'].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.sqs.all()
        self.assertEqual(int(results[21].pk), 18)
        self.assertEqual(len(connections['default'].queries), 1)

    def test_count(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        sqs = self.sqs.all()
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(len(sqs), 23)
        self.assertEqual(sqs.count(), 23)
        # Should only execute one query to count the length of the result set.
        self.assertEqual(len(connections['default'].queries), 1)

    def test_manual_iter(self):
        results = self.sqs.all()

        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, [2, 7, 12, 17, 1, 6, 11, 16, 23, 5, 10, 15, 22, 4, 9, 14, 19, 21, 3, 8, 13, 18, 20])
        self.assertEqual(len(connections['default'].queries), 3)

    def test_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.sqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections['default'].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(connections['default'].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(connections['default'].queries), 2)

    def test_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        self.assertEqual(self.sqs._cache_is_full(), False)
        results = self.sqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections['default'].queries), 3)

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
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND content__contains="pants:rule">')
        self.assertEqual(sqs.query.build_query(), u'("pants\\:rule")')
        self.assertEqual(len(sqs), 0)

    # Regressions

    @unittest.expectedFailure
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
        sqs = self.sqs.raw_search('text:index')
        page_1 = [result.pk for result in sqs[0:10]]
        page_2 = [result.pk for result in sqs[10:20]]

        for pk in page_2:
            if pk in page_1:
                self.fail("Result with id '%s' seen more than once in the results." % pk)

    # RelatedSearchQuerySet Tests

    def test_related_load_all(self):
        sqs = self.rsqs.load_all()
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue(len(sqs) > 0)
        self.assertEqual(sqs[0].object.foo, u'In addition, you may specify other fields to be populated along with the document. In this case, we also index the user who authored the document as well as the date the document was published. The variable you assign the SearchField to should directly map to the field your search backend is expecting. You instantiate most search fields with a parameter that points to the attribute of the object to populate that field with.')

    def test_related_load_all_queryset(self):
        sqs = self.rsqs.load_all()
        self.assertEqual(len(sqs._load_all_querysets), 0)

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual(sorted([obj.object.id for obj in sqs]), range(2, 24))

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=10))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], [12, 17, 11, 16, 23, 15, 22, 14, 19, 21, 13, 18, 20])
        self.assertEqual([obj.object.id for obj in sqs[10:20]], [13, 18, 20])

    def test_related_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        sqs = self.rsqs.all()
        results = [int(result.pk) for result in sqs]
        self.assertEqual(results, [2, 7, 12, 17, 1, 6, 11, 16, 23, 5, 10, 15, 22, 4, 9, 14, 19, 21, 3, 8, 13, 18, 20])
        self.assertEqual(len(connections['default'].queries), 4)

    def test_related_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [7, 12, 17, 1, 6, 11, 16, 23, 5, 10])
        self.assertEqual(len(connections['default'].queries), 3)

        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual(int(results[21].pk), 18)
        self.assertEqual(len(connections['default'].queries), 4)

        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[20:30]], [13, 18, 20])
        self.assertEqual(len(connections['default'].queries), 4)

    def test_related_manual_iter(self):
        results = self.rsqs.all()

        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = sorted([int(result.pk) for result in results._manual_iter()])
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(connections['default'].queries), 4)

    def test_related_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        results = self.rsqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections['default'].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(connections['default'].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(connections['default'].queries), 2)

    def test_related_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)
        self.assertEqual(self.rsqs._cache_is_full(), False)
        results = self.rsqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections['default'].queries), 5)

    def test_quotes_regression(self):
        sqs = self.sqs.auto_query(u"44°48'40''N 20°28'32''E")
        # Should not have empty terms.
        self.assertEqual(sqs.query.build_query(), u"(44\xb048'40''N 20\xb028'32''E)")
        # Should not cause Elasticsearch to 500.
        self.assertEqual(sqs.count(), 0)

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

        # Reset to default.
        sqs = self.sqs.result_class(None).all()
        self.assertTrue(isinstance(sqs[0], SearchResult))


class LiveElasticsearchMoreLikeThisTestCase(TestCase):
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(LiveElasticsearchMoreLikeThisTestCase, self).setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchMockModelSearchIndex()
        self.sammi = ElasticsearchAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi, self.sammi])
        connections['default']._index = self.ui

        self.sqs = SearchQuerySet()

        self.smmi.update()
        self.sammi.update()


    def tearDown(self):
        # Restore.
        connections['default']._index = self.old_ui
        super(LiveElasticsearchMoreLikeThisTestCase, self).tearDown()

    @unittest.expectedFailure
    def test_more_like_this(self):
        mlt = self.sqs.more_like_this(MockModel.objects.get(pk=1))
        self.assertEqual(mlt.count(), 4)
        self.assertEqual([result.pk for result in mlt], [u'2', u'6', u'16', u'23'])
        self.assertEqual(len([result.pk for result in mlt]), 4)

        alt_mlt = self.sqs.filter(name='daniel3').more_like_this(MockModel.objects.get(pk=2))
        self.assertEqual(alt_mlt.count(), 6)
        self.assertEqual([result.pk for result in alt_mlt], [u'2', u'6', u'16', u'23', u'1', u'11'])
        self.assertEqual(len([result.pk for result in alt_mlt]), 6)

        alt_mlt_with_models = self.sqs.models(MockModel).more_like_this(MockModel.objects.get(pk=1))
        self.assertEqual(alt_mlt_with_models.count(), 4)
        self.assertEqual([result.pk for result in alt_mlt_with_models], [u'2', u'6', u'16', u'23'])
        self.assertEqual(len([result.pk for result in alt_mlt_with_models]), 4)

        if hasattr(MockModel.objects, 'defer'):
            # Make sure MLT works with deferred bits.
            mi = MockModel.objects.defer('foo').get(pk=1)
            self.assertEqual(mi._deferred, True)
            deferred = self.sqs.models(MockModel).more_like_this(mi)
            self.assertEqual(deferred.count(), 0)
            self.assertEqual([result.pk for result in deferred], [])
            self.assertEqual(len([result.pk for result in deferred]), 0)

        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(isinstance(self.sqs.result_class(MockSearchResult).more_like_this(MockModel.objects.get(pk=1))[0], MockSearchResult))



class LiveElasticsearchAutocompleteTestCase(TestCase):
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(LiveElasticsearchAutocompleteTestCase, self).setUp()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchAutocompleteMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui

        self.sqs = SearchQuerySet()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Reboot the schema.
        self.sb = connections['default'].get_backend()
        self.sb.setup()

        self.smmi.update()

    def tearDown(self):
        # Restore.
        connections['default']._index = self.old_ui
        super(LiveElasticsearchAutocompleteTestCase, self).tearDown()

    def test_build_schema(self):
        self.sb = connections['default'].get_backend()
        content_name, mapping = self.sb.build_schema(self.ui.all_searchfields())
        self.assertEqual(mapping, {
            'name_auto': {
                'index': 'analyzed',
                'term_vector': 'with_positions_offsets',
                'type': 'string',
                'analyzer': 'edgengram_analyzer',
                'boost': 1.0,
                'store': 'yes'
            },
            'text': {
                'index': 'analyzed',
                'term_vector': 'with_positions_offsets',
                'type': 'string',
                'analyzer': 'snowball',
                'boost': 1.0,
                'store': 'yes'
            },
            'pub_date': {
                'index': 'analyzed',
                'boost': 1.0,
                'store': 'yes',
                'type': 'date'
            },
            'name': {
                'index': 'analyzed',
                'term_vector': 'with_positions_offsets',
                'type': 'string',
                'analyzer': 'snowball',
                'boost': 1.0,
                'store': 'yes'
            },
            'text_auto': {
                'index': 'analyzed',
                'term_vector': 'with_positions_offsets',
                'type': 'string',
                'analyzer': 'edgengram_analyzer',
                'boost': 1.0,
                'store': 'yes'
            }
        })

    def test_autocomplete(self):
        autocomplete = self.sqs.autocomplete(text_auto='mod')
        self.assertEqual(autocomplete.count(), 5)
        self.assertEqual([result.pk for result in autocomplete], [u'1', u'12', u'14', u'6', u'7'])
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


class LiveElasticsearchRoundTripTestCase(TestCase):
    def setUp(self):
        super(LiveElasticsearchRoundTripTestCase, self).setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.srtsi = ElasticsearchRoundTripSearchIndex()
        self.ui.build(indexes=[self.srtsi])
        connections['default']._index = self.ui
        self.sb = connections['default'].get_backend()

        self.sqs = SearchQuerySet()

        # Fake indexing.
        mock = MockModel()
        mock.id = 1
        self.sb.update(self.srtsi, [mock])

    def tearDown(self):
        # Restore.
        connections['default']._index = self.old_ui
        super(LiveElasticsearchRoundTripTestCase, self).tearDown()

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


if test_pickling:
    class LiveElasticsearchPickleTestCase(TestCase):
        fixtures = ['bulk_data.json']

        def setUp(self):
            super(LiveElasticsearchPickleTestCase, self).setUp()

            # Wipe it clean.
            clear_elasticsearch_index()

            # Stow.
            self.old_ui = connections['default'].get_unified_index()
            self.ui = UnifiedIndex()
            self.smmi = ElasticsearchMockModelSearchIndex()
            self.sammi = ElasticsearchAnotherMockModelSearchIndex()
            self.ui.build(indexes=[self.smmi, self.sammi])
            connections['default']._index = self.ui

            self.sqs = SearchQuerySet()

            self.smmi.update()
            self.sammi.update()

        def tearDown(self):
            # Restore.
            connections['default']._index = self.old_ui
            super(LiveElasticsearchPickleTestCase, self).tearDown()

        def test_pickling(self):
            results = self.sqs.all()

            for res in results:
                # Make sure the cache is full.
                pass

            in_a_pickle = pickle.dumps(results)
            like_a_cuke = pickle.loads(in_a_pickle)
            self.assertEqual(len(like_a_cuke), len(results))
            self.assertEqual(like_a_cuke[0].id, results[0].id)


class ElasticsearchBoostBackendTestCase(TestCase):
    def setUp(self):
        super(ElasticsearchBoostBackendTestCase, self).setUp()

        # Wipe it clean.
        self.raw_es = pyelasticsearch.ElasticSearch(settings.HAYSTACK_CONNECTIONS['default']['URL'])
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = ElasticsearchBoostMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui
        self.sb = connections['default'].get_backend()

        self.sample_objs = []

        for i in xrange(1, 5):
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
        connections['default']._index = self.old_ui
        super(ElasticsearchBoostBackendTestCase, self).tearDown()

    def raw_search(self, query):
        return self.raw_es.search('*:*', index=settings.HAYSTACK_CONNECTIONS['default']['INDEX_NAME'])

    def test_boost(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search('*:*')['hits']['total'], 4)

        results = SearchQuerySet().filter(SQ(author='daniel') | SQ(editor='daniel'))

        self.assertEqual([result.id for result in results], [
            'core.afourthmockmodel.3',
            'core.afourthmockmodel.1',
            'core.afourthmockmodel.2',
            'core.afourthmockmodel.4'
        ])
