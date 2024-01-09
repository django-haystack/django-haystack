import datetime
import warnings

from django.conf import settings

from haystack.backends import BaseEngine
from haystack.backends.elasticsearch_backend import (
    ElasticsearchSearchBackend,
    ElasticsearchSearchQuery,
)
from haystack.constants import DJANGO_CT
from haystack.exceptions import MissingDependency
from haystack.utils import get_identifier, get_model_ct

try:
    import elasticsearch

    if not ((2, 0, 0) <= elasticsearch.__version__ < (3, 0, 0)):
        raise ImportError
    from elasticsearch.helpers import bulk, scan

    warnings.warn(
        "ElasticSearch 2.x support deprecated, will be removed in 4.0",
        DeprecationWarning,
    )
except ImportError:
    raise MissingDependency(
        "The 'elasticsearch2' backend requires the \
                            installation of 'elasticsearch>=2.0.0,<3.0.0'. \
                            Please refer to the documentation."
    )


class Elasticsearch2SearchBackend(ElasticsearchSearchBackend):
    def __init__(self, connection_alias, **connection_options):
        super().__init__(connection_alias, **connection_options)
        self.content_field_name = None

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
                    **self._get_doc_type_option(),
                )
                actions = (
                    {"_op_type": "delete", "_id": doc["_id"]} for doc in generator
                )
                bulk(
                    self.conn,
                    actions=actions,
                    index=self.index_name,
                    **self._get_doc_type_option(),
                )
                self.conn.indices.refresh(index=self.index_name)

        except elasticsearch.TransportError:
            if not self.silently_fail:
                raise

            if models is not None:
                self.log.exception(
                    "Failed to clear Elasticsearch index of models '%s'",
                    ",".join(models_to_delete),
                )
            else:
                self.log.exception("Failed to clear Elasticsearch index")

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
    ):
        kwargs = super().build_search_kwargs(
            query_string,
            sort_by,
            start_offset,
            end_offset,
            fields,
            highlight,
            spelling_query=spelling_query,
            within=within,
            dwithin=dwithin,
            distance_point=distance_point,
            models=models,
            limit_to_registered_models=limit_to_registered_models,
            result_class=result_class,
        )

        filters = []
        if start_offset is not None:
            kwargs["from"] = start_offset

        if end_offset is not None:
            kwargs["size"] = end_offset - start_offset

        if narrow_queries is None:
            narrow_queries = set()

        if facets is not None:
            kwargs.setdefault("aggs", {})

            for facet_fieldname, extra_options in facets.items():
                facet_options = {
                    "meta": {"_type": "terms"},
                    "terms": {"field": facet_fieldname},
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

        for q in narrow_queries:
            filters.append({"query_string": {"query": q}})

        # if we want to filter, change the query type to filteres
        if filters:
            kwargs["query"] = {"filtered": {"query": kwargs.pop("query")}}
            filtered = kwargs["query"]["filtered"]
            if "filter" in filtered:
                if "bool" in filtered["filter"].keys():
                    another_filters = kwargs["query"]["filtered"]["filter"]["bool"][
                        "must"
                    ]
                else:
                    another_filters = [kwargs["query"]["filtered"]["filter"]]
            else:
                another_filters = filters

            if len(another_filters) == 1:
                kwargs["query"]["filtered"]["filter"] = another_filters[0]
            else:
                kwargs["query"]["filtered"]["filter"] = {
                    "bool": {"must": another_filters}
                }

        return kwargs

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
            # https://www.elastic.co/guide/en/elasticsearch/reference/2.2/query-dsl-mlt-query.html
            mlt_query = {
                "query": {
                    "more_like_this": {
                        "fields": [field_name],
                        "like": [{"_id": doc_id}],
                    }
                }
            }

            narrow_queries = []

            if additional_query_string and additional_query_string != "*:*":
                additional_filter = {
                    "query": {"query_string": {"query": additional_query_string}}
                }
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
                        "filtered": {
                            "query": mlt_query["query"],
                            "filter": {"bool": {"must": list(narrow_queries)}},
                        }
                    }
                }

            raw_results = self.conn.search(
                body=mlt_query,
                index=self.index_name,
                _source=True,
                **self._get_doc_type_option(),
                **params,
            )
        except elasticsearch.TransportError:
            if not self.silently_fail:
                raise

            self.log.exception(
                "Failed to fetch More Like This from Elasticsearch for document '%s'",
                doc_id,
            )
            raw_results = {}

        return self._process_results(raw_results, result_class=result_class)

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


class Elasticsearch2SearchQuery(ElasticsearchSearchQuery):
    pass


class Elasticsearch2SearchEngine(BaseEngine):
    backend = Elasticsearch2SearchBackend
    query = Elasticsearch2SearchQuery
