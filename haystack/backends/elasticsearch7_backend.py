import datetime
import warnings

from django.conf import settings

import haystack
from haystack.backends import BaseEngine
from haystack.backends.elasticsearch_backend import (
    ElasticsearchSearchBackend,
    ElasticsearchSearchQuery,
)
from haystack.constants import DEFAULT_OPERATOR, DJANGO_CT, DJANGO_ID, FUZZINESS
from haystack.exceptions import MissingDependency
from haystack.utils import get_identifier, get_model_ct

try:
    import elasticsearch

    if not ((7, 0, 0) <= elasticsearch.__version__ < (8, 0, 0)):
        raise ImportError
    from elasticsearch.helpers import bulk, scan
except ImportError:
    raise MissingDependency(
        "The 'elasticsearch7' backend requires the \
                            installation of 'elasticsearch>=7.0.0,<8.0.0'. \
                            Please refer to the documentation."
    )


DEFAULT_FIELD_MAPPING = {
    "type": "text",
    "analyzer": "snowball",
}
FIELD_MAPPINGS = {
    "edge_ngram": {
        "type": "text",
        "analyzer": "edgengram_analyzer",
    },
    "ngram": {
        "type": "text",
        "analyzer": "ngram_analyzer",
    },
    "date": {"type": "date"},
    "datetime": {"type": "date"},
    "location": {"type": "geo_point"},
    "boolean": {"type": "boolean"},
    "float": {"type": "float"},
    "long": {"type": "long"},
    "integer": {"type": "long"},
}


class Elasticsearch7SearchBackend(ElasticsearchSearchBackend):
    # Settings to add an n-gram & edge n-gram analyzer.
    DEFAULT_SETTINGS = {
        "settings": {
            "index": {
                "max_ngram_diff": 2,
            },
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_ngram",
                            "lowercase",
                        ],
                    },
                    "edgengram_analyzer": {
                        "tokenizer": "standard",
                        "filter": [
                            "haystack_edgengram",
                            "lowercase",
                        ],
                    },
                },
                "filter": {
                    "haystack_ngram": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 4,
                    },
                    "haystack_edgengram": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 15,
                    },
                },
            },
        },
    }

    def __init__(self, connection_alias, **connection_options):
        super().__init__(connection_alias, **connection_options)
        self.content_field_name = None

    def _get_doc_type_option(self):
        # ES7 does not support a doc_type option
        return {}

    def _get_current_mapping(self, field_mapping):
        # ES7 does not support a doc_type option
        return {"properties": field_mapping}

    def clear(self, models=None, commit=True):
        """
        Clears the backend of all documents/objects for a collection of models.

        :param models: List or tuple of models to clear.
        :param commit: Not used.
        """
        if models is not None:
            assert isinstance(models, (list, tuple))

        try:
            if models is None:
                self.conn.indices.delete(index=self.index_name, ignore=404)
                self.setup_complete = False
                self.existing_mapping = {}
                self.content_field_name = None
            else:
                models_to_delete = []

                for model in models:
                    models_to_delete.append("%s:%s" % (DJANGO_CT, get_model_ct(model)))

                # Delete using scroll API
                query = {
                    "query": {"query_string": {"query": " OR ".join(models_to_delete)}}
                }
                generator = scan(
                    self.conn,
                    query=query,
                    index=self.index_name,
                )
                actions = (
                    {"_op_type": "delete", "_id": doc["_id"]} for doc in generator
                )
                bulk(
                    self.conn,
                    actions=actions,
                    index=self.index_name,
                )
                self.conn.indices.refresh(index=self.index_name)

        except elasticsearch.TransportError as e:
            if not self.silently_fail:
                raise

            if models is not None:
                self.log.error(
                    "Failed to clear Elasticsearch index of models '%s': %s",
                    ",".join(models_to_delete),
                    e,
                    exc_info=True,
                )
            else:
                self.log.error(
                    "Failed to clear Elasticsearch index: %s", e, exc_info=True
                )

    def build_search_kwargs(
        self,
        query_string,
        sort_by=None,
        start_offset=0,
        end_offset=None,
        fields="",
        highlight=False,
        facets=None,
        date_facets=None,
        query_facets=None,
        narrow_queries=None,
        spelling_query=None,
        within=None,
        dwithin=None,
        distance_point=None,
        models=None,
        limit_to_registered_models=None,
        result_class=None,
        **extra_kwargs
    ):
        index = haystack.connections[self.connection_alias].get_unified_index()
        content_field = index.document_field

        if query_string == "*:*":
            kwargs = {"query": {"match_all": {}}}
        else:
            kwargs = {
                "query": {
                    "query_string": {
                        "default_field": content_field,
                        "default_operator": DEFAULT_OPERATOR,
                        "query": query_string,
                        "analyze_wildcard": True,
                        "fuzziness": FUZZINESS,
                    }
                }
            }

        filters = []

        if fields:
            if isinstance(fields, (list, set)):
                fields = " ".join(fields)

            kwargs["stored_fields"] = fields

        if sort_by is not None:
            order_list = []
            for field, direction in sort_by:
                if field == "distance" and distance_point:
                    # Do the geo-enabled sort.
                    lng, lat = distance_point["point"].coords
                    sort_kwargs = {
                        "_geo_distance": {
                            distance_point["field"]: [lng, lat],
                            "order": direction,
                            "unit": "km",
                        }
                    }
                else:
                    if field == "distance":
                        warnings.warn(
                            "In order to sort by distance, you must call the '.distance(...)' method."
                        )

                    # Regular sorting.
                    sort_kwargs = {field: {"order": direction}}

                order_list.append(sort_kwargs)

            kwargs["sort"] = order_list

        # From/size offsets don't seem to work right in Elasticsearch's DSL. :/
        # if start_offset is not None:
        #     kwargs['from'] = start_offset

        # if end_offset is not None:
        #     kwargs['size'] = end_offset - start_offset

        if highlight:
            # `highlight` can either be True or a dictionary containing custom parameters
            # which will be passed to the backend and may override our default settings:

            kwargs["highlight"] = {"fields": {content_field: {}}}

            if isinstance(highlight, dict):
                kwargs["highlight"].update(highlight)

        if self.include_spelling:
            kwargs["suggest"] = {
                "suggest": {
                    "text": spelling_query or query_string,
                    "term": {
                        # Using content_field here will result in suggestions of stemmed words.
                        "field": "text",  # ES7 does not support '_all' field
                    },
                }
            }

        if narrow_queries is None:
            narrow_queries = set()

        if facets is not None:
            kwargs.setdefault("aggs", {})

            for facet_fieldname, extra_options in facets.items():
                facet_options = {
                    "meta": {"_type": "terms"},
                    "terms": {"field": index.get_facet_fieldname(facet_fieldname)},
                }
                if "order" in extra_options:
                    facet_options["meta"]["order"] = extra_options.pop("order")
                # Special cases for options applied at the facet level (not the terms level).
                if extra_options.pop("global_scope", False):
                    # Renamed "global_scope" since "global" is a python keyword.
                    facet_options["global"] = True
                if "facet_filter" in extra_options:
                    facet_options["facet_filter"] = extra_options.pop("facet_filter")
                facet_options["terms"].update(extra_options)
                kwargs["aggs"][facet_fieldname] = facet_options

        if date_facets is not None:
            kwargs.setdefault("aggs", {})

            for facet_fieldname, value in date_facets.items():
                # Need to detect on gap_by & only add amount if it's more than one.
                interval = value.get("gap_by").lower()

                # Need to detect on amount (can't be applied on months or years).
                if value.get("gap_amount", 1) != 1 and interval not in (
                    "month",
                    "year",
                ):
                    # Just the first character is valid for use.
                    interval = "%s%s" % (value["gap_amount"], interval[:1])

                kwargs["aggs"][facet_fieldname] = {
                    "meta": {"_type": "date_histogram"},
                    "date_histogram": {"field": facet_fieldname, "interval": interval},
                    "aggs": {
                        facet_fieldname: {
                            "date_range": {
                                "field": facet_fieldname,
                                "ranges": [
                                    {
                                        "from": self._from_python(
                                            value.get("start_date")
                                        ),
                                        "to": self._from_python(value.get("end_date")),
                                    }
                                ],
                            }
                        }
                    },
                }

        if query_facets is not None:
            kwargs.setdefault("aggs", {})

            for facet_fieldname, value in query_facets:
                kwargs["aggs"][facet_fieldname] = {
                    "meta": {"_type": "query"},
                    "filter": {"query_string": {"query": value}},
                }

        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(
                settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
            )

        if models and len(models):
            model_choices = sorted(get_model_ct(model) for model in models)
        elif limit_to_registered_models:
            # Using narrow queries, limit the results to only models handled
            # with the current routers.
            model_choices = self.build_models_list()
        else:
            model_choices = []

        if len(model_choices) > 0:
            filters.append({"terms": {DJANGO_CT: model_choices}})

        for q in narrow_queries:
            filters.append({"query_string": {"query": q}})

        if within is not None:
            filters.append(self._build_search_query_within(within))

        if dwithin is not None:
            filters.append(self._build_search_query_dwithin(dwithin))

        # if we want to filter, change the query type to bool
        if filters:
            kwargs["query"] = {"bool": {"must": kwargs.pop("query")}}
            if len(filters) == 1:
                kwargs["query"]["bool"]["filter"] = filters[0]
            else:
                kwargs["query"]["bool"]["filter"] = {"bool": {"must": filters}}

        if extra_kwargs:
            kwargs.update(extra_kwargs)

        return kwargs

    def _build_search_query_dwithin(self, dwithin):
        lng, lat = dwithin["point"].coords
        distance = "%(dist).6f%(unit)s" % {"dist": dwithin["distance"].km, "unit": "km"}
        return {
            "geo_distance": {
                "distance": distance,
                dwithin["field"]: {"lat": lat, "lon": lng},
            }
        }

    def _build_search_query_within(self, within):
        from haystack.utils.geo import generate_bounding_box

        ((south, west), (north, east)) = generate_bounding_box(
            within["point_1"], within["point_2"]
        )
        return {
            "geo_bounding_box": {
                within["field"]: {
                    "top_left": {"lat": north, "lon": west},
                    "bottom_right": {"lat": south, "lon": east},
                }
            }
        }

    def more_like_this(
        self,
        model_instance,
        additional_query_string=None,
        start_offset=0,
        end_offset=None,
        models=None,
        limit_to_registered_models=None,
        result_class=None,
        **kwargs
    ):
        from haystack import connections

        if not self.setup_complete:
            self.setup()

        # Deferred models will have a different class ("RealClass_Deferred_fieldname")
        # which won't be in our registry:
        model_klass = model_instance._meta.concrete_model

        index = (
            connections[self.connection_alias]
            .get_unified_index()
            .get_index(model_klass)
        )
        field_name = index.get_content_field()
        params = {}

        if start_offset is not None:
            params["from_"] = start_offset

        if end_offset is not None:
            params["size"] = end_offset - start_offset

        doc_id = get_identifier(model_instance)

        try:
            # More like this Query
            # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-mlt-query.html
            mlt_query = {
                "query": {
                    "more_like_this": {
                        "fields": [field_name],
                        "like": [
                            {
                                "_index": self.index_name,
                                "_id": doc_id,
                            },
                        ],
                    }
                }
            }

            narrow_queries = []

            if additional_query_string and additional_query_string != "*:*":
                additional_filter = {"query_string": {"query": additional_query_string}}
                narrow_queries.append(additional_filter)

            if limit_to_registered_models is None:
                limit_to_registered_models = getattr(
                    settings, "HAYSTACK_LIMIT_TO_REGISTERED_MODELS", True
                )

            if models and len(models):
                model_choices = sorted(get_model_ct(model) for model in models)
            elif limit_to_registered_models:
                # Using narrow queries, limit the results to only models handled
                # with the current routers.
                model_choices = self.build_models_list()
            else:
                model_choices = []

            if len(model_choices) > 0:
                model_filter = {"terms": {DJANGO_CT: model_choices}}
                narrow_queries.append(model_filter)

            if len(narrow_queries) > 0:
                mlt_query = {
                    "query": {
                        "bool": {
                            "must": mlt_query["query"],
                            "filter": {"bool": {"must": list(narrow_queries)}},
                        }
                    }
                }

            raw_results = self.conn.search(
                body=mlt_query, index=self.index_name, _source=True, **params
            )
        except elasticsearch.TransportError as e:
            if not self.silently_fail:
                raise

            self.log.error(
                "Failed to fetch More Like This from Elasticsearch for document '%s': %s",
                doc_id,
                e,
                exc_info=True,
            )
            raw_results = {}

        return self._process_results(raw_results, result_class=result_class)

    def _process_hits(self, raw_results):
        return raw_results.get("hits", {}).get("total", {}).get("value", 0)

    def _process_results(
        self,
        raw_results,
        highlight=False,
        result_class=None,
        distance_point=None,
        geo_sort=False,
    ):
        results = super()._process_results(
            raw_results, highlight, result_class, distance_point, geo_sort
        )
        facets = {}
        if "aggregations" in raw_results:
            facets = {"fields": {}, "dates": {}, "queries": {}}

            for facet_fieldname, facet_info in raw_results["aggregations"].items():
                facet_type = facet_info["meta"]["_type"]
                if facet_type == "terms":
                    facets["fields"][facet_fieldname] = [
                        (individual["key"], individual["doc_count"])
                        for individual in facet_info["buckets"]
                    ]
                    if "order" in facet_info["meta"]:
                        if facet_info["meta"]["order"] == "reverse_count":
                            srt = sorted(
                                facets["fields"][facet_fieldname], key=lambda x: x[1]
                            )
                            facets["fields"][facet_fieldname] = srt
                elif facet_type == "date_histogram":
                    # Elasticsearch provides UTC timestamps with an extra three
                    # decimals of precision, which datetime barfs on.
                    facets["dates"][facet_fieldname] = [
                        (
                            datetime.datetime.utcfromtimestamp(
                                individual["key"] / 1000
                            ),
                            individual["doc_count"],
                        )
                        for individual in facet_info["buckets"]
                    ]
                elif facet_type == "query":
                    facets["queries"][facet_fieldname] = facet_info["doc_count"]
        results["facets"] = facets
        return results

    def _get_common_mapping(self):
        return {
            DJANGO_CT: {
                "type": "keyword",
            },
            DJANGO_ID: {
                "type": "keyword",
            },
        }

    def build_schema(self, fields):
        content_field_name = ""
        mapping = self._get_common_mapping()

        for _, field_class in fields.items():
            field_mapping = FIELD_MAPPINGS.get(
                field_class.field_type, DEFAULT_FIELD_MAPPING
            ).copy()
            if field_class.boost != 1.0:
                field_mapping["boost"] = field_class.boost

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            # Do this last to override `text` fields.
            if field_mapping["type"] == "text":
                if field_class.indexed is False or hasattr(field_class, "facet_for"):
                    field_mapping["type"] = "keyword"
                    del field_mapping["analyzer"]

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)


class Elasticsearch7SearchQuery(ElasticsearchSearchQuery):
    def add_field_facet(self, field, **options):
        self.facets[field] = options.copy()


class Elasticsearch7SearchEngine(BaseEngine):
    backend = Elasticsearch7SearchBackend
    query = Elasticsearch7SearchQuery
