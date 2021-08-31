import datetime
import logging as std_logging
import operator
import pickle
import unittest
from decimal import Decimal

import elasticsearch
from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from haystack import connections, indexes, reset_search_queries
from haystack.exceptions import SkipDocument
from haystack.inputs import AutoQuery
from haystack.models import SearchResult
from haystack.query import SQ, RelatedSearchQuerySet, SearchQuerySet
from haystack.utils import log as logging
from haystack.utils.loading import UnifiedIndex

from ..core.models import AFourthMockModel, AnotherMockModel, ASixthMockModel, MockModel
from ..mocks import MockSearchResult


def clear_elasticsearch_index():
    # Wipe it clean.
    raw_es = elasticsearch.Elasticsearch(
        settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
    )
    try:
        raw_es.indices.delete(
            index=settings.HAYSTACK_CONNECTIONS["elasticsearch"]["INDEX_NAME"]
        )
        raw_es.indices.refresh()
    except elasticsearch.TransportError:
        pass

    # Since we've just completely deleted the index, we'll reset setup_complete so the next access will
    # correctly define the mappings:
    connections["elasticsearch"].get_backend().setup_complete = False


class Elasticsearch7MockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="author", faceted=True)
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return MockModel


class Elasticsearch7MockSearchIndexWithSkipDocument(Elasticsearch7MockSearchIndex):
    def prepare_text(self, obj):
        if obj.author == "daniel3":
            raise SkipDocument
        return "Indexed!\n%s" % obj.id


class Elasticsearch7MockSpellingIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr="author", faceted=True)
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return MockModel

    def prepare_text(self, obj):
        return obj.foo


class Elasticsearch7MaintainTypeMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month

    def get_model(self):
        return MockModel


class Elasticsearch7MockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr="foo", document=True)
    name = indexes.CharField(model_attr="author")
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return MockModel


class Elasticsearch7AnotherMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr="author")
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return AnotherMockModel

    def prepare_text(self, obj):
        return "You might be searching for the user %s" % obj.author


class Elasticsearch7BoostMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(
        document=True,
        use_template=True,
        template_name="search/indexes/core/mockmodel_template.txt",
    )
    author = indexes.CharField(model_attr="author", weight=2.0)
    editor = indexes.CharField(model_attr="editor")
    pub_date = indexes.DateTimeField(model_attr="pub_date")

    def get_model(self):
        return AFourthMockModel

    def prepare(self, obj):
        data = super().prepare(obj)

        if obj.pk == 4:
            data["boost"] = 5.0

        return data


class Elasticsearch7FacetingMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    author = indexes.CharField(model_attr="author", faceted=True)
    editor = indexes.CharField(model_attr="editor", faceted=True)
    pub_date = indexes.DateField(model_attr="pub_date", faceted=True)
    facet_field = indexes.FacetCharField(model_attr="author")

    def prepare_text(self, obj):
        return "%s %s" % (obj.author, obj.editor)

    def get_model(self):
        return AFourthMockModel


class Elasticsearch7RoundTripSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, default="")
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
        prepped = super().prepare(obj)
        prepped.update(
            {
                "text": "This is some example text.",
                "name": "Mister Pants",
                "is_active": True,
                "post_count": 25,
                "average_rating": 3.6,
                "price": Decimal("24.99"),
                "pub_date": datetime.date(2009, 11, 21),
                "created": datetime.datetime(2009, 11, 21, 21, 31, 00),
                "tags": ["staff", "outdoor", "activist", "scientist"],
                "sites": [3, 5, 1],
            }
        )
        return prepped


class Elasticsearch7ComplexFacetsMockSearchIndex(
    indexes.SearchIndex, indexes.Indexable
):
    text = indexes.CharField(document=True, default="")
    name = indexes.CharField(faceted=True)
    is_active = indexes.BooleanField(faceted=True)
    post_count = indexes.IntegerField()
    post_count_i = indexes.FacetIntegerField(facet_for="post_count")
    average_rating = indexes.FloatField(faceted=True)
    pub_date = indexes.DateField(faceted=True)
    created = indexes.DateTimeField(faceted=True)
    sites = indexes.MultiValueField(faceted=True)
    facet_field = indexes.FacetCharField(model_attr="name")

    def get_model(self):
        return MockModel


class Elasticsearch7AutocompleteMockModelSearchIndex(
    indexes.SearchIndex, indexes.Indexable
):
    text = indexes.CharField(model_attr="foo", document=True)
    name = indexes.CharField(model_attr="author")
    pub_date = indexes.DateTimeField(model_attr="pub_date")
    text_auto = indexes.EdgeNgramField(model_attr="foo")
    name_auto = indexes.EdgeNgramField(model_attr="author")

    def get_model(self):
        return MockModel


class Elasticsearch7SpatialSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr="name", document=True)
    location = indexes.LocationField()

    def prepare_location(self, obj):
        return "%s,%s" % (obj.lat, obj.lon)

    def get_model(self):
        return ASixthMockModel


class TestSettings(TestCase):
    def test_kwargs_are_passed_on(self):
        from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend

        backend = ElasticsearchSearchBackend(
            "alias",
            **{
                "URL": settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"],
                "INDEX_NAME": "testing",
                "KWARGS": {"max_retries": 42},
            }
        )

        self.assertEqual(backend.conn.transport.max_retries, 42)


class Elasticsearch7SearchBackendTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Wipe it clean.
        self.raw_es = elasticsearch.Elasticsearch(
            settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
        )
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockSearchIndex()
        self.smmidni = Elasticsearch7MockSearchIndexWithSkipDocument()
        self.smtmmi = Elasticsearch7MaintainTypeMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui
        self.sb = connections["elasticsearch"].get_backend()

        # Force the backend to rebuild the mapping each time.
        self.sb.existing_mapping = {}
        self.sb.setup()

        self.sample_objs = []

        for i in range(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = "daniel%s" % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()
        self.sb.silently_fail = True

    def raw_search(self, query):
        try:
            return self.raw_es.search(
                q="*:*",
                index=settings.HAYSTACK_CONNECTIONS["elasticsearch"]["INDEX_NAME"],
            )
        except elasticsearch.TransportError:
            return {}

    def test_non_silent(self):
        bad_sb = connections["elasticsearch"].backend(
            "bad",
            URL="http://omg.wtf.bbq:1000/",
            INDEX_NAME="whatver",
            SILENTLY_FAIL=False,
            TIMEOUT=1,
        )

        try:
            bad_sb.update(self.smmi, self.sample_objs)
            self.fail()
        except:
            pass

        try:
            bad_sb.remove("core.mockmodel.1")
            self.fail()
        except:
            pass

        try:
            bad_sb.clear()
            self.fail()
        except:
            pass

        try:
            bad_sb.search("foo")
            self.fail()
        except:
            pass

    def test_update_no_documents(self):
        url = settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
        index_name = settings.HAYSTACK_CONNECTIONS["elasticsearch"]["INDEX_NAME"]

        sb = connections["elasticsearch"].backend(
            "elasticsearch", URL=url, INDEX_NAME=index_name, SILENTLY_FAIL=True
        )
        self.assertEqual(sb.update(self.smmi, []), None)

        sb = connections["elasticsearch"].backend(
            "elasticsearch", URL=url, INDEX_NAME=index_name, SILENTLY_FAIL=False
        )
        try:
            sb.update(self.smmi, [])
            self.fail()
        except:
            pass

    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)

        # Check what Elasticsearch thinks is there.
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 3)
        self.assertEqual(
            sorted(
                [res["_source"] for res in self.raw_search("*:*")["hits"]["hits"]],
                key=lambda x: x["id"],
            ),
            [
                {
                    "django_id": "1",
                    "django_ct": "core.mockmodel",
                    "name": "daniel1",
                    "name_exact": "daniel1",
                    "text": "Indexed!\n1\n",
                    "pub_date": "2009-02-24T00:00:00",
                    "id": "core.mockmodel.1",
                },
                {
                    "django_id": "2",
                    "django_ct": "core.mockmodel",
                    "name": "daniel2",
                    "name_exact": "daniel2",
                    "text": "Indexed!\n2\n",
                    "pub_date": "2009-02-23T00:00:00",
                    "id": "core.mockmodel.2",
                },
                {
                    "django_id": "3",
                    "django_ct": "core.mockmodel",
                    "name": "daniel3",
                    "name_exact": "daniel3",
                    "text": "Indexed!\n3\n",
                    "pub_date": "2009-02-22T00:00:00",
                    "id": "core.mockmodel.3",
                },
            ],
        )

    def test_update_with_SkipDocument_raised(self):
        self.sb.update(self.smmidni, self.sample_objs)

        # Check what Elasticsearch thinks is there.
        res = self.raw_search("*:*")["hits"]
        self.assertEqual(res["total"]["value"], 2)
        self.assertListEqual(
            sorted([x["_source"]["id"] for x in res["hits"]]),
            ["core.mockmodel.1", "core.mockmodel.2"],
        )

    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 3)

        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 2)
        self.assertEqual(
            sorted(
                [res["_source"] for res in self.raw_search("*:*")["hits"]["hits"]],
                key=operator.itemgetter("django_id"),
            ),
            [
                {
                    "django_id": "2",
                    "django_ct": "core.mockmodel",
                    "name": "daniel2",
                    "name_exact": "daniel2",
                    "text": "Indexed!\n2\n",
                    "pub_date": "2009-02-23T00:00:00",
                    "id": "core.mockmodel.2",
                },
                {
                    "django_id": "3",
                    "django_ct": "core.mockmodel",
                    "name": "daniel3",
                    "name_exact": "daniel3",
                    "text": "Indexed!\n3\n",
                    "pub_date": "2009-02-22T00:00:00",
                    "id": "core.mockmodel.3",
                },
            ],
        )

    def test_remove_succeeds_on_404(self):
        self.sb.silently_fail = False
        self.sb.remove("core.mockmodel.421")

    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            3,
        )

        self.sb.clear()
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            0,
        )

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            3,
        )

        self.sb.clear([AnotherMockModel])
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            3,
        )

        self.sb.clear([MockModel])
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            0,
        )

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            3,
        )

        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(
            self.raw_search("*:*").get("hits", {}).get("total", {}).get("value", 0),
            0,
        )

    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 3)

        self.assertEqual(self.sb.search(""), {"hits": 0, "results": []})
        self.assertEqual(self.sb.search("*:*")["hits"], 3)
        self.assertEqual(
            set([result.pk for result in self.sb.search("*:*")["results"]]),
            {"2", "1", "3"},
        )

        self.assertEqual(self.sb.search("", highlight=True), {"hits": 0, "results": []})
        self.assertEqual(self.sb.search("Index", highlight=True)["hits"], 3)
        self.assertEqual(
            sorted(
                [
                    result.highlighted[0]
                    for result in self.sb.search("Index", highlight=True)["results"]
                ]
            ),
            [
                "<em>Indexed</em>!\n1",
                "<em>Indexed</em>!\n2",
                "<em>Indexed</em>!\n3",
            ],
        )

        self.assertEqual(self.sb.search("Indx")["hits"], 0)
        self.assertEqual(self.sb.search("indaxed")["spelling_suggestion"], "index")
        self.assertEqual(
            self.sb.search("arf", spelling_query="indexyd")["spelling_suggestion"],
            "index",
        )

        self.assertEqual(
            self.sb.search("", facets={"name": {}}), {"hits": 0, "results": []}
        )
        results = self.sb.search("Index", facets={"name": {}})
        self.assertEqual(results["hits"], 3)
        self.assertSetEqual(
            set(results["facets"]["fields"]["name"]),
            {("daniel3", 1), ("daniel2", 1), ("daniel1", 1)},
        )

        self.assertEqual(
            self.sb.search(
                "",
                date_facets={
                    "pub_date": {
                        "start_date": datetime.date(2008, 1, 1),
                        "end_date": datetime.date(2009, 4, 1),
                        "gap_by": "month",
                        "gap_amount": 1,
                    }
                },
            ),
            {"hits": 0, "results": []},
        )
        results = self.sb.search(
            "Index",
            date_facets={
                "pub_date": {
                    "start_date": datetime.date(2008, 1, 1),
                    "end_date": datetime.date(2009, 4, 1),
                    "gap_by": "month",
                    "gap_amount": 1,
                }
            },
        )
        self.assertEqual(results["hits"], 3)
        self.assertEqual(
            results["facets"]["dates"]["pub_date"],
            [(datetime.datetime(2009, 2, 1, 0, 0), 3)],
        )

        self.assertEqual(
            self.sb.search("", query_facets=[("name", "[* TO e]")]),
            {"hits": 0, "results": []},
        )
        results = self.sb.search("Index", query_facets=[("name", "[* TO e]")])
        self.assertEqual(results["hits"], 3)
        self.assertEqual(results["facets"]["queries"], {"name": 3})

        self.assertEqual(
            self.sb.search("", narrow_queries={"name:daniel1"}),
            {"hits": 0, "results": []},
        )
        results = self.sb.search("Index", narrow_queries={"name:daniel1"})
        self.assertEqual(results["hits"], 1)

        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(
            isinstance(
                self.sb.search("index", result_class=MockSearchResult)["results"][0],
                MockSearchResult,
            )
        )

        # Check the use of ``limit_to_registered_models``.
        self.assertEqual(
            self.sb.search("", limit_to_registered_models=False),
            {"hits": 0, "results": []},
        )
        self.assertEqual(
            self.sb.search("*:*", limit_to_registered_models=False)["hits"], 3
        )
        self.assertEqual(
            sorted(
                [
                    result.pk
                    for result in self.sb.search(
                        "*:*", limit_to_registered_models=False
                    )["results"]
                ]
            ),
            ["1", "2", "3"],
        )

        # Stow.
        old_limit_to_registered_models = getattr(
            settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
        )
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False

        self.assertEqual(self.sb.search(""), {"hits": 0, "results": []})
        self.assertEqual(self.sb.search("*:*")["hits"], 3)
        self.assertEqual(
            sorted([result.pk for result in self.sb.search("*:*")["results"]]),
            ["1", "2", "3"],
        )

        # Restore.
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = old_limit_to_registered_models

    def test_spatial_search_parameters(self):
        from django.contrib.gis.geos import Point

        p1 = Point(1.23, 4.56)
        kwargs = self.sb.build_search_kwargs(
            "*:*",
            distance_point={"field": "location", "point": p1},
            sort_by=(("distance", "desc"),),
        )

        self.assertIn("sort", kwargs)
        self.assertEqual(1, len(kwargs["sort"]))
        geo_d = kwargs["sort"][0]["_geo_distance"]

        # ElasticSearch supports the GeoJSON-style lng, lat pairs so unlike Solr the values should be
        # in the same order as we used to create the Point():
        # http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/query-dsl-geo-distance-filter.html#_lat_lon_as_array_4

        self.assertDictEqual(
            geo_d, {"location": [1.23, 4.56], "unit": "km", "order": "desc"}
        )

    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 3)

        # A functional MLT example with enough data to work is below. Rely on
        # this to ensure the API is correct enough.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])["hits"], 0)
        self.assertEqual(
            [
                result.pk
                for result in self.sb.more_like_this(self.sample_objs[0])["results"]
            ],
            [],
        )

    def test_build_schema(self):
        old_ui = connections["elasticsearch"].get_unified_index()

        (content_field_name, mapping) = self.sb.build_schema(old_ui.all_searchfields())
        self.assertEqual(content_field_name, "text")
        self.assertEqual(len(mapping), 4 + 2)  # + 2 management fields
        self.assertEqual(
            mapping,
            {
                "django_ct": {
                    "type": "keyword",
                },
                "django_id": {
                    "type": "keyword",
                },
                "text": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "name": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "name_exact": {
                    "type": "keyword",
                },
                "pub_date": {
                    "type": "date",
                },
            },
        )

        ui = UnifiedIndex()
        ui.build(indexes=[Elasticsearch7ComplexFacetsMockSearchIndex()])
        (content_field_name, mapping) = self.sb.build_schema(ui.all_searchfields())
        self.assertEqual(content_field_name, "text")
        self.assertEqual(len(mapping), 16 + 2)
        self.assertEqual(
            mapping,
            {
                "django_ct": {
                    "type": "keyword",
                },
                "django_id": {
                    "type": "keyword",
                },
                "text": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "name": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "name_exact": {
                    "type": "keyword",
                },
                "is_active": {
                    "type": "boolean",
                },
                "is_active_exact": {
                    "type": "boolean",
                },
                "post_count": {
                    "type": "long",
                },
                "post_count_i": {
                    "type": "long",
                },
                "average_rating": {
                    "type": "float",
                },
                "average_rating_exact": {
                    "type": "float",
                },
                "pub_date": {
                    "type": "date",
                },
                "pub_date_exact": {
                    "type": "date",
                },
                "created": {
                    "type": "date",
                },
                "created_exact": {
                    "type": "date",
                },
                "sites": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "sites_exact": {
                    "type": "keyword",
                },
                "facet_field": {
                    "type": "keyword",
                },
            },
        )

    def test_verify_type(self):
        old_ui = connections["elasticsearch"].get_unified_index()
        ui = UnifiedIndex()
        smtmmi = Elasticsearch7MaintainTypeMockSearchIndex()
        ui.build(indexes=[smtmmi])
        connections["elasticsearch"]._index = ui
        sb = connections["elasticsearch"].get_backend()
        sb.update(smtmmi, self.sample_objs)

        self.assertEqual(sb.search("*:*")["hits"], 3)
        self.assertEqual(
            [result.month for result in sb.search("*:*")["results"]], ["02", "02", "02"]
        )
        connections["elasticsearch"]._index = old_ui


class CaptureHandler(std_logging.Handler):
    logs_seen = []

    def emit(self, record):
        CaptureHandler.logs_seen.append(record)


class FailedElasticsearch7SearchBackendTestCase(TestCase):
    def setUp(self):
        self.sample_objs = []

        for i in range(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = "daniel%s" % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

        # Stow.
        # Point the backend at a URL that doesn't exist so we can watch the
        # sparks fly.
        self.old_es_url = settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
        settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"] = (
            "%s/foo/" % self.old_es_url
        )
        self.cap = CaptureHandler()
        logging.getLogger("haystack").addHandler(self.cap)
        config = apps.get_app_config("haystack")
        logging.getLogger("haystack").removeHandler(config.stream)

        # Setup the rest of the bits.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockSearchIndex()
        ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = ui
        self.sb = connections["elasticsearch"].get_backend()

    def tearDown(self):
        # Restore.
        settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"] = self.old_es_url
        connections["elasticsearch"]._index = self.old_ui
        config = apps.get_app_config("haystack")
        logging.getLogger("haystack").removeHandler(self.cap)
        logging.getLogger("haystack").addHandler(config.stream)

    @unittest.expectedFailure
    def test_all_cases(self):
        # Prior to the addition of the try/except bits, these would all fail miserably.
        self.assertEqual(len(CaptureHandler.logs_seen), 0)

        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(CaptureHandler.logs_seen), 1)

        self.sb.remove(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 2)

        self.sb.search("search")
        self.assertEqual(len(CaptureHandler.logs_seen), 3)

        self.sb.more_like_this(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 4)

        self.sb.clear([MockModel])
        self.assertEqual(len(CaptureHandler.logs_seen), 5)

        self.sb.clear()
        self.assertEqual(len(CaptureHandler.logs_seen), 6)


class LiveElasticsearch7SearchQueryTestCase(TestCase):
    fixtures = ["base_data.json"]

    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui
        self.sb = connections["elasticsearch"].get_backend()
        self.sq = connections["elasticsearch"].get_query()

        # Force indexing of the content.
        self.smmi.update(using="elasticsearch")

    def tearDown(self):
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_log_query(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)

        with self.settings(DEBUG=False):
            len(self.sq.get_results())
            self.assertEqual(len(connections["elasticsearch"].queries), 0)

        with self.settings(DEBUG=True):
            # Redefine it to clear out the cached results.
            self.sq = connections["elasticsearch"].query(using="elasticsearch")
            self.sq.add_filter(SQ(name="bar"))
            len(self.sq.get_results())
            self.assertEqual(len(connections["elasticsearch"].queries), 1)
            self.assertEqual(
                connections["elasticsearch"].queries[0]["query_string"], "name:(bar)"
            )

            # And again, for good measure.
            self.sq = connections["elasticsearch"].query("elasticsearch")
            self.sq.add_filter(SQ(name="bar"))
            self.sq.add_filter(SQ(text="moof"))
            len(self.sq.get_results())
            self.assertEqual(len(connections["elasticsearch"].queries), 2)
            self.assertEqual(
                connections["elasticsearch"].queries[0]["query_string"], "name:(bar)"
            )
            self.assertEqual(
                connections["elasticsearch"].queries[1]["query_string"],
                "(name:(bar) AND text:(moof))",
            )


lssqstc_all_loaded = None


@override_settings(DEBUG=True)
class LiveElasticsearch7SearchQuerySetTestCase(TestCase):
    """Used to test actual implementation details of the SearchQuerySet."""

    fixtures = ["bulk_data.json"]

    def setUp(self):
        super().setUp()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui

        self.sqs = SearchQuerySet("elasticsearch")
        self.rsqs = RelatedSearchQuerySet("elasticsearch")

        # Ugly but not constantly reindexing saves us almost 50% runtime.
        global lssqstc_all_loaded

        if lssqstc_all_loaded is None:
            lssqstc_all_loaded = True

            # Wipe it clean.
            clear_elasticsearch_index()

            # Force indexing of the content.
            self.smmi.update(using="elasticsearch")

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_load_all(self):
        sqs = self.sqs.order_by("pub_date").load_all()
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue(len(sqs) > 0)
        self.assertEqual(
            sqs[2].object.foo,
            "In addition, you may specify other fields to be populated along with the document. In this case, we also index the user who authored the document as well as the date the document was published. The variable you assign the SearchField to should directly map to the field your search backend is expecting. You instantiate most search fields with a parameter that points to the attribute of the object to populate that field with.",
        )

    def test_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        sqs = self.sqs.all()
        results = sorted([int(result.pk) for result in sqs])
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.sqs.all().order_by("pub_date")
        self.assertEqual(
            [int(result.pk) for result in results[1:11]],
            [3, 2, 4, 5, 6, 7, 8, 9, 10, 11],
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.sqs.all().order_by("pub_date")
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

    def test_values_slicing(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)

        # TODO: this would be a good candidate for refactoring into a TestCase subclass shared across backends

        # The values will come back as strings because Hasytack doesn't assume PKs are integers.
        # We'll prepare this set once since we're going to query the same results in multiple ways:
        expected_pks = [str(i) for i in [3, 2, 4, 5, 6, 7, 8, 9, 10, 11]]

        results = self.sqs.all().order_by("pub_date").values("pk")
        self.assertListEqual([i["pk"] for i in results[1:11]], expected_pks)

        results = self.sqs.all().order_by("pub_date").values_list("pk")
        self.assertListEqual([i[0] for i in results[1:11]], expected_pks)

        results = self.sqs.all().order_by("pub_date").values_list("pk", flat=True)
        self.assertListEqual(results[1:11], expected_pks)

        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_count(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        sqs = self.sqs.all()
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(sqs.count(), 23)
        self.assertEqual(len(sqs), 23)
        self.assertEqual(sqs.count(), 23)
        # Should only execute one query to count the length of the result set.
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

    def test_manual_iter(self):
        results = self.sqs.all()

        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = set([int(result.pk) for result in results._manual_iter()])
        self.assertEqual(
            results,
            {
                2,
                7,
                12,
                17,
                1,
                6,
                11,
                16,
                23,
                5,
                10,
                15,
                22,
                4,
                9,
                14,
                19,
                21,
                3,
                8,
                13,
                18,
                20,
            },
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.sqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(
            len([result for result in results._result_cache if result is not None]), 10
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(
            len([result for result in results._result_cache if result is not None]), 20
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 2)

    def test_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        self.assertEqual(self.sqs._cache_is_full(), False)
        results = self.sqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test___and__(self):
        sqs1 = self.sqs.filter(content="foo")
        sqs2 = self.sqs.filter(content="bar")
        sqs = sqs1 & sqs2

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), "((foo) AND (bar))")

        # Now for something more complex...
        sqs3 = self.sqs.exclude(title="moof").filter(
            SQ(content="foo") | SQ(content="baz")
        )
        sqs4 = self.sqs.filter(content="bar")
        sqs = sqs3 & sqs4

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 3)
        self.assertEqual(
            sqs.query.build_query(),
            "(NOT (title:(moof)) AND ((foo) OR (baz)) AND (bar))",
        )

    def test___or__(self):
        sqs1 = self.sqs.filter(content="foo")
        sqs2 = self.sqs.filter(content="bar")
        sqs = sqs1 | sqs2

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), "((foo) OR (bar))")

        # Now for something more complex...
        sqs3 = self.sqs.exclude(title="moof").filter(
            SQ(content="foo") | SQ(content="baz")
        )
        sqs4 = self.sqs.filter(content="bar").models(MockModel)
        sqs = sqs3 | sqs4

        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(
            sqs.query.build_query(),
            "((NOT (title:(moof)) AND ((foo) OR (baz))) OR (bar))",
        )

    def test_auto_query(self):
        # Ensure bits in exact matches get escaped properly as well.
        # This will break horrifically if escaping isn't working.
        sqs = self.sqs.auto_query('"pants:rule"')
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(
            repr(sqs.query.query_filter), '<SQ: AND content__content="pants:rule">'
        )
        self.assertEqual(sqs.query.build_query(), '("pants\\:rule")')
        self.assertEqual(len(sqs), 0)

    # Regressions

    def test_regression_proper_start_offsets(self):
        sqs = self.sqs.filter(text="index")
        self.assertNotEqual(sqs.count(), 0)

        id_counts = {}

        for item in sqs:
            if item.id in id_counts:
                id_counts[item.id] += 1
            else:
                id_counts[item.id] = 1

        for key, value in id_counts.items():
            if value > 1:
                self.fail(
                    "Result with id '%s' seen more than once in the results." % key
                )

    def test_regression_raw_search_breaks_slicing(self):
        sqs = self.sqs.raw_search("text:index")
        page_1 = [result.pk for result in sqs[0:10]]
        page_2 = [result.pk for result in sqs[10:20]]

        for pk in page_2:
            if pk in page_1:
                self.fail(
                    "Result with id '%s' seen more than once in the results." % pk
                )

    # RelatedSearchQuerySet Tests

    def test_related_load_all(self):
        sqs = self.rsqs.order_by("pub_date").load_all()
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertTrue(len(sqs) > 0)
        self.assertEqual(
            sqs[2].object.foo,
            "In addition, you may specify other fields to be populated along with the document. In this case, we also index the user who authored the document as well as the date the document was published. The variable you assign the SearchField to should directly map to the field your search backend is expecting. You instantiate most search fields with a parameter that points to the attribute of the object to populate that field with.",
        )

    def test_related_load_all_queryset(self):
        sqs = self.rsqs.load_all().order_by("pub_date")
        self.assertEqual(len(sqs._load_all_querysets), 0)

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual(sorted([obj.object.id for obj in sqs]), list(range(2, 24)))

        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=10))
        self.assertTrue(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual(
            set([obj.object.id for obj in sqs]),
            {12, 17, 11, 16, 23, 15, 22, 14, 19, 21, 13, 18, 20},
        )
        self.assertEqual(set([obj.object.id for obj in sqs[10:20]]), {21, 22, 23})

    def test_related_iter(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        sqs = self.rsqs.all()
        results = set([int(result.pk) for result in sqs])
        self.assertEqual(
            results,
            {
                2,
                7,
                12,
                17,
                1,
                6,
                11,
                16,
                23,
                5,
                10,
                15,
                22,
                4,
                9,
                14,
                19,
                21,
                3,
                8,
                13,
                18,
                20,
            },
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_related_slice(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.rsqs.all().order_by("pub_date")
        self.assertEqual(
            [int(result.pk) for result in results[1:11]],
            [3, 2, 4, 5, 6, 7, 8, 9, 10, 11],
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.rsqs.all().order_by("pub_date")
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.rsqs.all().order_by("pub_date")
        self.assertEqual(
            set([int(result.pk) for result in results[20:30]]), {21, 22, 23}
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 1)

    def test_related_manual_iter(self):
        results = self.rsqs.all()

        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = sorted([int(result.pk) for result in results._manual_iter()])
        self.assertEqual(results, list(range(1, 24)))
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_related_fill_cache(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results = self.rsqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(
            len([result for result in results._result_cache if result is not None]), 10
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(
            len([result for result in results._result_cache if result is not None]), 20
        )
        self.assertEqual(len(connections["elasticsearch"].queries), 2)

    def test_related_cache_is_full(self):
        reset_search_queries()
        self.assertEqual(len(connections["elasticsearch"].queries), 0)
        self.assertEqual(self.rsqs._cache_is_full(), False)
        results = self.rsqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(connections["elasticsearch"].queries), 3)

    def test_quotes_regression(self):
        sqs = self.sqs.auto_query("44°48'40''N 20°28'32''E")
        # Should not have empty terms.
        self.assertEqual(sqs.query.build_query(), "(44\xb048'40''N 20\xb028'32''E)")
        # Should not cause Elasticsearch to 500.
        self.assertEqual(sqs.count(), 0)

        sqs = self.sqs.auto_query("blazing")
        self.assertEqual(sqs.query.build_query(), "(blazing)")
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query("blazing saddles")
        self.assertEqual(sqs.query.build_query(), "(blazing saddles)")
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles')
        self.assertEqual(sqs.query.build_query(), '(\\"blazing saddles)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles"')
        self.assertEqual(sqs.query.build_query(), '("blazing saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles"')
        self.assertEqual(sqs.query.build_query(), '(mel "blazing saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing \'saddles"')
        self.assertEqual(sqs.query.build_query(), '(mel "blazing \'saddles")')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query("mel \"blazing ''saddles\"")
        self.assertEqual(sqs.query.build_query(), "(mel \"blazing ''saddles\")")
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query("mel \"blazing ''saddles\"'")
        self.assertEqual(sqs.query.build_query(), "(mel \"blazing ''saddles\" ')")
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query("mel \"blazing ''saddles\"'\"")
        self.assertEqual(sqs.query.build_query(), "(mel \"blazing ''saddles\" '\\\")")
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles" mel')
        self.assertEqual(sqs.query.build_query(), '("blazing saddles" mel)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('"blazing saddles" mel brooks')
        self.assertEqual(sqs.query.build_query(), '("blazing saddles" mel brooks)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles" brooks')
        self.assertEqual(sqs.query.build_query(), '(mel "blazing saddles" brooks)')
        self.assertEqual(sqs.count(), 0)
        sqs = self.sqs.auto_query('mel "blazing saddles" "brooks')
        self.assertEqual(sqs.query.build_query(), '(mel "blazing saddles" \\"brooks)')
        self.assertEqual(sqs.count(), 0)

    def test_query_generation(self):
        sqs = self.sqs.filter(
            SQ(content=AutoQuery("hello world")) | SQ(title=AutoQuery("hello world"))
        )
        self.assertEqual(
            sqs.query.build_query(), "((hello world) OR title:(hello world))"
        )

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


@override_settings(DEBUG=True)
class LiveElasticsearch7SpellingTestCase(TestCase):
    """Used to test actual implementation details of the SearchQuerySet."""

    fixtures = ["bulk_data.json"]

    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Reboot the schema.
        self.sb = connections["elasticsearch"].get_backend()
        self.sb.setup()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockSpellingIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui

        self.sqs = SearchQuerySet("elasticsearch")

        self.smmi.update(using="elasticsearch")

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_spelling(self):
        # self.assertEqual(
        #     self.sqs.auto_query("structurd").spelling_suggestion(), "structured"
        # )
        self.assertEqual(
            self.sqs.auto_query("structurd").spelling_suggestion(), "structur"
        )
        # self.assertEqual(self.sqs.spelling_suggestion("structurd"), "structured")
        self.assertEqual(self.sqs.spelling_suggestion("structurd"), "structur")
        # self.assertEqual(
        #     self.sqs.auto_query("srchindex instanc").spelling_suggestion(),
        #     "searchindex instance",
        # )
        self.assertEqual(
            self.sqs.auto_query("srchindex instanc").spelling_suggestion(),
            "searchindex instanc",
        )
        # self.assertEqual(
        #     self.sqs.spelling_suggestion("srchindex instanc"), "searchindex instance"
        # )
        self.assertEqual(
            self.sqs.spelling_suggestion("srchindex instanc"), "searchindex instanc"
        )


class LiveElasticsearch7MoreLikeThisTestCase(TestCase):
    fixtures = ["bulk_data.json"]

    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockModelSearchIndex()
        self.sammi = Elasticsearch7AnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi, self.sammi])
        connections["elasticsearch"]._index = self.ui

        self.sqs = SearchQuerySet("elasticsearch")

        self.smmi.update(using="elasticsearch")
        self.sammi.update(using="elasticsearch")

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_more_like_this(self):
        mlt = self.sqs.more_like_this(MockModel.objects.get(pk=1))
        results = [result.pk for result in mlt]
        self.assertEqual(22, mlt.count())
        self.assertEqual(
            {"14", "6", "10", "4", "5", "22", "12", "3", "7", "2"},
            set(results),
        )
        self.assertEqual(10, len(results))

        alt_mlt = self.sqs.filter(name="daniel3").more_like_this(
            MockModel.objects.get(pk=2),
        )
        results = [result.pk for result in alt_mlt]
        self.assertEqual(11, alt_mlt.count())
        self.assertEqual(
            {"1", "2", "13", "19", "23", "3", "22", "17", "16", "10"},
            set(results),
        )
        self.assertEqual(10, len(results))

        alt_mlt_with_models = self.sqs.models(MockModel).more_like_this(
            MockModel.objects.get(pk=1)
        )
        results = [result.pk for result in alt_mlt_with_models]
        self.assertEqual(20, alt_mlt_with_models.count())
        self.assertEqual(
            {"10", "7", "5", "4", "22", "3", "2", "12", "6", "14"},
            set(results),
        )
        self.assertEqual(len(results), 10)

        if hasattr(MockModel.objects, "defer"):
            # Make sure MLT works with deferred bits.
            qs = MockModel.objects.defer("foo")
            self.assertEqual(qs.query.deferred_loading[1], True)
            deferred = self.sqs.models(MockModel).more_like_this(qs.get(pk=1))
            self.assertEqual(20, deferred.count())
            self.assertEqual(
                {"12", "6", "2", "3", "10", "5", "14", "7", "22", "4"},
                {result.pk for result in deferred},
            )
            self.assertEqual(len([result.pk for result in deferred]), 10)

        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(
            isinstance(
                self.sqs.result_class(MockSearchResult).more_like_this(
                    MockModel.objects.get(pk=1)
                )[0],
                MockSearchResult,
            )
        )


class LiveElasticsearch7AutocompleteTestCase(TestCase):
    fixtures = ["bulk_data.json"]

    def setUp(self):
        super().setUp()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7AutocompleteMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui

        self.sqs = SearchQuerySet("elasticsearch")

        # Wipe it clean.
        clear_elasticsearch_index()

        # Reboot the schema.
        self.sb = connections["elasticsearch"].get_backend()
        self.sb.setup()

        self.smmi.update(using="elasticsearch")

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_build_schema(self):
        self.sb = connections["elasticsearch"].get_backend()
        content_name, mapping = self.sb.build_schema(self.ui.all_searchfields())
        self.assertEqual(
            mapping,
            {
                "django_ct": {
                    "type": "keyword",
                },
                "django_id": {
                    "type": "keyword",
                },
                "text": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "name": {
                    "type": "text",
                    "analyzer": "snowball",
                },
                "pub_date": {
                    "type": "date",
                },
                "text_auto": {
                    "type": "text",
                    "analyzer": "edgengram_analyzer",
                },
                "name_auto": {
                    "type": "text",
                    "analyzer": "edgengram_analyzer",
                },
            },
        )

    def test_autocomplete(self):
        autocomplete = self.sqs.autocomplete(text_auto="mod")
        self.assertEqual(autocomplete.count(), 16)
        self.assertEqual(
            set([result.pk for result in autocomplete]),
            {
                "1",
                "12",
                "6",
                "14",
                "7",
                "4",
                "23",
                "17",
                "13",
                "18",
                "20",
                "22",
                "19",
                "15",
                "10",
                "2",
            },
        )
        self.assertTrue("mod" in autocomplete[0].text.lower())
        self.assertTrue("mod" in autocomplete[1].text.lower())
        self.assertTrue("mod" in autocomplete[2].text.lower())
        self.assertTrue("mod" in autocomplete[3].text.lower())
        self.assertTrue("mod" in autocomplete[4].text.lower())
        self.assertEqual(len([result.pk for result in autocomplete]), 16)

        # Test multiple words.
        autocomplete_2 = self.sqs.autocomplete(text_auto="your mod")
        self.assertEqual(autocomplete_2.count(), 13)
        self.assertEqual(
            set([result.pk for result in autocomplete_2]),
            {"1", "6", "2", "14", "12", "13", "10", "19", "4", "20", "23", "22", "15"},
        )
        map_results = {result.pk: result for result in autocomplete_2}
        self.assertTrue("your" in map_results["1"].text.lower())
        self.assertTrue("mod" in map_results["1"].text.lower())
        self.assertTrue("your" in map_results["6"].text.lower())
        self.assertTrue("mod" in map_results["6"].text.lower())
        self.assertTrue("your" in map_results["2"].text.lower())
        self.assertEqual(len([result.pk for result in autocomplete_2]), 13)

        # Test multiple fields.
        autocomplete_3 = self.sqs.autocomplete(text_auto="Django", name_auto="dan")
        self.assertEqual(autocomplete_3.count(), 4)
        self.assertEqual(
            set([result.pk for result in autocomplete_3]), {"12", "1", "22", "14"}
        )
        self.assertEqual(len([result.pk for result in autocomplete_3]), 4)

        # Test numbers in phrases
        autocomplete_4 = self.sqs.autocomplete(text_auto="Jen 867")
        self.assertEqual(autocomplete_4.count(), 1)
        self.assertEqual(set([result.pk for result in autocomplete_4]), {"20"})

        # Test numbers alone
        autocomplete_4 = self.sqs.autocomplete(text_auto="867")
        self.assertEqual(autocomplete_4.count(), 1)
        self.assertEqual(set([result.pk for result in autocomplete_4]), {"20"})


class LiveElasticsearch7RoundTripTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.srtsi = Elasticsearch7RoundTripSearchIndex()
        self.ui.build(indexes=[self.srtsi])
        connections["elasticsearch"]._index = self.ui
        self.sb = connections["elasticsearch"].get_backend()

        self.sqs = SearchQuerySet("elasticsearch")

        # Fake indexing.
        mock = MockModel()
        mock.id = 1
        self.sb.update(self.srtsi, [mock])

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_round_trip(self):
        results = self.sqs.filter(id="core.mockmodel.1")

        # Sanity check.
        self.assertEqual(results.count(), 1)

        # Check the individual fields.
        result = results[0]
        self.assertEqual(result.id, "core.mockmodel.1")
        self.assertEqual(result.text, "This is some example text.")
        self.assertEqual(result.name, "Mister Pants")
        self.assertEqual(result.is_active, True)
        self.assertEqual(result.post_count, 25)
        self.assertEqual(result.average_rating, 3.6)
        self.assertEqual(result.price, "24.99")
        self.assertEqual(result.pub_date, datetime.date(2009, 11, 21))
        self.assertEqual(result.created, datetime.datetime(2009, 11, 21, 21, 31, 00))
        self.assertEqual(result.tags, ["staff", "outdoor", "activist", "scientist"])
        self.assertEqual(result.sites, [3, 5, 1])


class LiveElasticsearch7PickleTestCase(TestCase):
    fixtures = ["bulk_data.json"]

    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Reboot the schema.
        sb = connections["elasticsearch"].get_backend()
        sb.setup()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7MockModelSearchIndex()
        self.sammi = Elasticsearch7AnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.smmi, self.sammi])
        connections["elasticsearch"]._index = self.ui

        self.sqs = SearchQuerySet("elasticsearch")

        self.smmi.update(using="elasticsearch")
        self.sammi.update(using="elasticsearch")

    def tearDown(self):
        # Restore.
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_pickling(self):
        results = self.sqs.all()

        for res in results:
            # Make sure the cache is full.
            pass

        in_a_pickle = pickle.dumps(results)
        like_a_cuke = pickle.loads(in_a_pickle)
        self.assertEqual(len(like_a_cuke), len(results))
        self.assertEqual(like_a_cuke[0].id, results[0].id)


class Elasticsearch7BoostBackendTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Wipe it clean.
        self.raw_es = elasticsearch.Elasticsearch(
            settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
        )
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7BoostMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui
        self.sb = connections["elasticsearch"].get_backend()

        self.sample_objs = []

        for i in range(1, 5):
            mock = AFourthMockModel()
            mock.id = i

            if i % 2:
                mock.author = "daniel"
                mock.editor = "david"
            else:
                mock.author = "david"
                mock.editor = "daniel"

            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def raw_search(self, query):
        return self.raw_es.search(
            q="*:*", index=settings.HAYSTACK_CONNECTIONS["elasticsearch"]["INDEX_NAME"]
        )

    def test_boost(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_search("*:*")["hits"]["total"]["value"], 4)

        results = SearchQuerySet(using="elasticsearch").filter(
            SQ(author="daniel") | SQ(editor="daniel")
        )

        self.assertEqual(
            set([result.id for result in results]),
            {
                "core.afourthmockmodel.4",
                "core.afourthmockmodel.3",
                "core.afourthmockmodel.1",
                "core.afourthmockmodel.2",
            },
        )

    def test__to_python(self):
        self.assertEqual(self.sb._to_python("abc"), "abc")
        self.assertEqual(self.sb._to_python("1"), 1)
        self.assertEqual(self.sb._to_python("2653"), 2653)
        self.assertEqual(self.sb._to_python("25.5"), 25.5)
        self.assertEqual(self.sb._to_python("[1, 2, 3]"), [1, 2, 3])
        self.assertEqual(
            self.sb._to_python('{"a": 1, "b": 2, "c": 3}'), {"a": 1, "c": 3, "b": 2}
        )
        self.assertEqual(
            self.sb._to_python("2009-05-09T16:14:00"),
            datetime.datetime(2009, 5, 9, 16, 14),
        )
        self.assertEqual(
            self.sb._to_python("2009-05-09T00:00:00"),
            datetime.datetime(2009, 5, 9, 0, 0),
        )
        self.assertEqual(self.sb._to_python(None), None)


class RecreateIndexTestCase(TestCase):
    def setUp(self):
        self.raw_es = elasticsearch.Elasticsearch(
            settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
        )

    def test_recreate_index(self):
        clear_elasticsearch_index()

        sb = connections["elasticsearch"].get_backend()
        sb.setup_complete = False
        sb.existing_mapping = {}
        self.content_field_name = None
        sb.silently_fail = True
        sb.setup()

        original_mapping = self.raw_es.indices.get_mapping(index=sb.index_name)

        sb.clear()
        sb.setup()

        try:
            updated_mapping = self.raw_es.indices.get_mapping(sb.index_name)
        except elasticsearch.NotFoundError:
            self.fail("There is no mapping after recreating the index")

        self.assertEqual(
            original_mapping,
            updated_mapping,
            "Mapping after recreating the index differs from the original one",
        )


class Elasticsearch7FacetingTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Wipe it clean.
        clear_elasticsearch_index()

        # Stow.
        self.old_ui = connections["elasticsearch"].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = Elasticsearch7FacetingMockSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections["elasticsearch"]._index = self.ui
        self.sb = connections["elasticsearch"].get_backend()

        # Force the backend to rebuild the mapping each time.
        self.sb.existing_mapping = {}
        self.sb.setup()

        self.sample_objs = []

        for i in range(1, 10):
            mock = AFourthMockModel()
            mock.id = i
            if i > 5:
                mock.editor = "George Taylor"
            else:
                mock.editor = "Perry White"
            if i % 2:
                mock.author = "Daniel Lindsley"
            else:
                mock.author = "Dan Watson"
            mock.pub_date = datetime.date(2013, 9, (i % 4) + 1)
            self.sample_objs.append(mock)

    def tearDown(self):
        connections["elasticsearch"]._index = self.old_ui
        super().tearDown()

    def test_facet(self):
        self.sb.update(self.smmi, self.sample_objs)
        counts = (
            SearchQuerySet("elasticsearch")
            .facet("author")
            .facet("editor")
            .facet_counts()
        )
        self.assertEqual(
            counts["fields"]["author"], [("Daniel Lindsley", 5), ("Dan Watson", 4)]
        )
        self.assertEqual(
            counts["fields"]["editor"], [("Perry White", 5), ("George Taylor", 4)]
        )
        counts = (
            SearchQuerySet("elasticsearch")
            .filter(content="white")
            .facet("facet_field", order="reverse_count")
            .facet_counts()
        )
        self.assertEqual(
            counts["fields"]["facet_field"], [("Dan Watson", 2), ("Daniel Lindsley", 3)]
        )

    def test_multiple_narrow(self):
        self.sb.update(self.smmi, self.sample_objs)
        counts = (
            SearchQuerySet("elasticsearch")
            .narrow('editor_exact:"Perry White"')
            .narrow('author_exact:"Daniel Lindsley"')
            .facet("author")
            .facet_counts()
        )
        self.assertEqual(counts["fields"]["author"], [("Daniel Lindsley", 3)])

    def test_narrow(self):
        self.sb.update(self.smmi, self.sample_objs)
        counts = (
            SearchQuerySet("elasticsearch")
            .facet("author")
            .facet("editor")
            .narrow('editor_exact:"Perry White"')
            .facet_counts()
        )
        self.assertEqual(
            counts["fields"]["author"], [("Daniel Lindsley", 3), ("Dan Watson", 2)]
        )
        self.assertEqual(counts["fields"]["editor"], [("Perry White", 5)])

    def test_date_facet(self):
        self.sb.update(self.smmi, self.sample_objs)
        start = datetime.date(2013, 9, 1)
        end = datetime.date(2013, 9, 30)
        # Facet by day
        counts = (
            SearchQuerySet("elasticsearch")
            .date_facet("pub_date", start_date=start, end_date=end, gap_by="day")
            .facet_counts()
        )
        self.assertEqual(
            counts["dates"]["pub_date"],
            [
                (datetime.datetime(2013, 9, 1), 2),
                (datetime.datetime(2013, 9, 2), 3),
                (datetime.datetime(2013, 9, 3), 2),
                (datetime.datetime(2013, 9, 4), 2),
            ],
        )
        # By month
        counts = (
            SearchQuerySet("elasticsearch")
            .date_facet("pub_date", start_date=start, end_date=end, gap_by="month")
            .facet_counts()
        )
        self.assertEqual(
            counts["dates"]["pub_date"], [(datetime.datetime(2013, 9, 1), 9)]
        )
