import datetime
import logging
import warnings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.loading import get_model
import haystack
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, log_query
from haystack.constants import ID, DJANGO_CT, DJANGO_ID, DEFAULT_OPERATOR
from haystack.exceptions import MissingDependency, MoreLikeThisError
from haystack.inputs import PythonData, Clean, Exact
from haystack.models import SearchResult
from haystack.utils import get_identifier
try:
    from django.db.models.sql.query import get_proxied_model
except ImportError:
    # Likely on Django 1.0
    get_proxied_model = None
try:
    import requests
except ImportError:
    raise MissingDependency("The 'elasticsearch' backend requires the installation of 'requests'.")
try:
    import pyelasticsearch
except ImportError:
    raise MissingDependency("The 'elasticsearch' backend requires the installation of 'pyelasticsearch'. Please refer to the documentation.")


class ElasticsearchSearchBackend(BaseSearchBackend):
    # Word reserved by Elasticsearch for special use.
    RESERVED_WORDS = (
        'AND',
        'NOT',
        'OR',
        'TO',
    )

    # Characters reserved by Elasticsearch for special use.
    # The '\\' must come first, so as not to overwrite the other slash replacements.
    RESERVED_CHARACTERS = (
        '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
        '[', ']', '^', '"', '~', '*', '?', ':',
    )

    # Settings to add an n-gram & edge n-gram analyzer.
    DEFAULT_SETTINGS = {
        'settings': {
            "analysis": {
                "analyzer": {
                    "ngram_analyzer": {
                        "type": "custom",
                        "tokenizer": "lowercase",
                        "filter": ["haystack_ngram"]
                    },
                    "edgengram_analyzer": {
                        "type": "custom",
                        "tokenizer": "lowercase",
                        "filter": ["haystack_edgengram"]
                    }
                },
                "tokenizer": {
                    "haystack_ngram_tokenizer": {
                        "type": "nGram",
                        "min_gram" : 3,
                        "max_gram" : 15,
                    },
                    "haystack_edgengram_tokenizer": {
                        "type": "edgeNGram",
                        "min_gram" : 2,
                        "max_gram" : 15,
                        "side": "front"
                    }
                },
                "filter" : {
                    "haystack_ngram" : {
                        "type" : "nGram",
                        "min_gram" : 3,
                        "max_gram" : 15
                    },
                    "haystack_edgengram" : {
                        "type" : "edgeNGram",
                        "min_gram" : 2,
                        "max_gram" : 15
                    }
                }
            }
        }
    }

    def __init__(self, connection_alias, **connection_options):
        super(ElasticsearchSearchBackend, self).__init__(connection_alias, **connection_options)

        if not 'URL' in connection_options:
            raise ImproperlyConfigured("You must specify a 'URL' in your settings for connection '%s'." % connection_alias)

        if not 'INDEX_NAME' in connection_options:
            raise ImproperlyConfigured("You must specify a 'INDEX_NAME' in your settings for connection '%s'." % connection_alias)

        self.conn = pyelasticsearch.ElasticSearch(connection_options['URL'], timeout=self.timeout)
        self.index_name = connection_options['INDEX_NAME']
        self.log = logging.getLogger('haystack')
        self.setup_complete = False
        self.existing_mapping = {}

    def setup(self):
        """
        Defers loading until needed.
        """
        # Get the existing mapping & cache it. We'll compare it
        # during the ``update`` & if it doesn't match, we'll put the new
        # mapping.
        try:
            self.existing_mapping = self.conn.get_mapping(indexes=[self.index_name])
        except Exception, e:
            if not self.silently_fail:
                raise

        unified_index = haystack.connections[self.connection_alias].get_unified_index()
        self.content_field_name, field_mapping = self.build_schema(unified_index.all_searchfields())
        current_mapping = {
            'modelresult': {
                'properties': field_mapping
            }
        }

        if current_mapping != self.existing_mapping:
            try:
                # Make sure the index is there first.
                self.conn.create_index(self.index_name, self.DEFAULT_SETTINGS)
                self.conn.put_mapping('modelresult', current_mapping, indexes=[self.index_name])
                self.existing_mapping = current_mapping
            except Exception, e:
                if not self.silently_fail:
                    raise

        self.setup_complete = True

    def update(self, index, iterable, commit=True):
        if not self.setup_complete:
            try:
                self.setup()
            except pyelasticsearch.ElasticSearchError, e:
                if not self.silently_fail:
                    raise

                self.log.error("Failed to add documents to Elasticsearch: %s", e)
                return

        try:
            prepped_docs = []

            for obj in iterable:
                prepped_data = index.full_prepare(obj)
                final_data = {}

                # Convert the data to make sure it's happy.
                for key, value in prepped_data.items():
                    final_data[key] = self.conn.from_python(value)

                prepped_docs.append(final_data)

            self.conn.bulk_index(self.index_name, 'modelresult', prepped_docs, id_field=ID)

            if commit:
                self.conn.refresh(indexes=[self.index_name])
        except (requests.RequestException, pyelasticsearch.ElasticSearchError), e:
            if not self.silently_fail:
                raise

            self.log.error("Failed to add documents to Elasticsearch: %s", e)

    def remove(self, obj_or_string, commit=True):
        doc_id = get_identifier(obj_or_string)

        if not self.setup_complete:
            try:
                self.setup()
            except pyelasticsearch.ElasticSearchError, e:
                if not self.silently_fail:
                    raise

                self.log.error("Failed to remove document '%s' from Elasticsearch: %s", doc_id, e)
                return

        try:
            self.conn.delete(self.index_name, 'modelresult', doc_id)

            if commit:
                self.conn.refresh(indexes=[self.index_name])
        except (requests.RequestException, pyelasticsearch.ElasticSearchError), e:
            if not self.silently_fail:
                raise

            self.log.error("Failed to remove document '%s' from Elasticsearch: %s", doc_id, e)

    def clear(self, models=[], commit=True):
        # We actually don't want to do this here, as mappings could be
        # very different.
        # if not self.setup_complete:
        #     self.setup()

        try:
            if not models:
                self.conn.delete_index(self.index_name)
            else:
                models_to_delete = []

                for model in models:
                    models_to_delete.append("%s:%s.%s" % (DJANGO_CT, model._meta.app_label, model._meta.module_name))

                # Delete by query in Elasticsearch asssumes you're dealing with
                # a ``query`` root object. :/
                self.conn.delete_by_query(self.index_name, 'modelresult', {'query_string': {'query': " OR ".join(models_to_delete)}})

            if commit:
                self.conn.refresh(indexes=[self.index_name])
        except (requests.RequestException, pyelasticsearch.ElasticSearchError), e:
            if not self.silently_fail:
                raise

            if len(models):
                self.log.error("Failed to clear Elasticsearch index of models '%s': %s", ','.join(models_to_delete), e)
            else:
                self.log.error("Failed to clear Elasticsearch index: %s", e)

    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None, within=None,
               dwithin=None, distance_point=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
        if len(query_string) == 0:
            return {
                'results': [],
                'hits': 0,
            }

        if not self.setup_complete:
            self.setup()

        index = haystack.connections[self.connection_alias].get_unified_index()
        content_field = index.document_field

        if query_string == '*:*':
            kwargs = {
                'query': {
                    'filtered': {
                        'query': {
                            'query_string': {
                                'query': '*:*',
                            },
                        },
                    },
                },
            }
        else:
            kwargs = {
                'query': {
                    'filtered': {
                        'query': {
                            'query_string': {
                                'default_field': content_field,
                                'default_operator': DEFAULT_OPERATOR,
                                'query': query_string,
                                'analyze_wildcard': True,
                                'auto_generate_phrase_queries': True,
                            },
                        },
                    },
                },
            }

        geo_sort = False

        if fields:
            if isinstance(fields, (list, set)):
                fields = " ".join(fields)

            kwargs['fields'] = fields

        if sort_by is not None:
            order_list = []
            for field, direction in sort_by:
                if field == 'distance' and distance_point:
                    # Do the geo-enabled sort.
                    lng, lat = distance_point['point'].get_coords()
                    sort_kwargs = {
                        "_geo_distance": {
                            distance_point['field']: [lng, lat],
                            "order" : direction,
                            "unit" : "km"
                        }
                    }
                else:
                    if field == 'distance':
                        warnings.warn("In order to sort by distance, you must call the '.distance(...)' method.")

                    # Regular sorting.
                    sort_kwargs = {field: {'order': direction}}

                order_list.append(sort_kwargs)

            kwargs['sort'] = order_list

        # From/size offsets don't seem to work right in Elasticsearch's DSL. :/
        # if start_offset is not None:
        #     kwargs['from'] = start_offset

        # if end_offset is not None:
        #     kwargs['size'] = end_offset - start_offset

        if highlight is True:
            kwargs['highlight'] = {
                'fields': {
                    content_field: {'store': 'yes'},
                }
            }

        if self.include_spelling is True:
            warnings.warn("Elasticsearch does not handle spelling suggestions.", Warning, stacklevel=2)

        if narrow_queries is None:
            narrow_queries = set()

        if facets is not None:
            kwargs.setdefault('facets', {})

            for facet_fieldname in facets:
                kwargs['facets'][facet_fieldname] = {
                    'terms': {
                        'field': facet_fieldname,
                    },
                }

        if date_facets is not None:
            kwargs.setdefault('facets', {})

            for facet_fieldname, value in date_facets.items():
                # Need to detect on gap_by & only add amount if it's more than one.
                interval = value.get('gap_by').lower()

                # Need to detect on amount (can't be applied on months or years).
                if value.get('gap_amount', 1) != 1 and not interval in ('month', 'year'):
                    # Just the first character is valid for use.
                    interval = "%s%s" % (value['gap_amount'], interval[:1])

                kwargs['facets'][facet_fieldname] = {
                    'date_histogram': {
                        'field': facet_fieldname,
                        'interval': interval,
                    },
                    'facet_filter': {
                        "range": {
                            facet_fieldname: {
                                'from': self.conn.from_python(value.get('start_date')),
                                'to': self.conn.from_python(value.get('end_date')),
                            }
                        }
                    }
                }

        if query_facets is not None:
            kwargs.setdefault('facets', {})

            for facet_fieldname, value in query_facets:
                kwargs['facets'][facet_fieldname] = {
                    'query': {
                        'query_string': {
                            'query': value,
                        }
                    },
                }

        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)

        if limit_to_registered_models:
            # Using narrow queries, limit the results to only models handled
            # with the current routers.
            registered_models = self.build_models_list()

            if len(registered_models) > 0:
                narrow_queries.add('%s:(%s)' % (DJANGO_CT, ' OR '.join(registered_models)))

        if narrow_queries:
            kwargs['query'].setdefault('filtered', {})
            kwargs['query']['filtered'].setdefault('filter', {})
            kwargs['query']['filtered']['filter'] = {
                'fquery': {
                    'query': {
                        'query_string': {
                            'query': u' AND '.join(list(narrow_queries)),
                        },
                    },
                    '_cache': True,
                }
            }

        if within is not None:
            from haystack.utils.geo import generate_bounding_box

            ((min_lat, min_lng), (max_lat, max_lng)) = generate_bounding_box(within['point_1'], within['point_2'])
            kwargs['query'].setdefault('filtered', {})
            kwargs['query']['filtered'].setdefault('filter', {})
            kwargs['query']['filtered']['filter'] = {
                "geo_bounding_box": {
                    within['field']: {
                        "top_left": {
                            "lat": max_lat,
                            "lon": max_lng
                        },
                        "bottom_right": {
                            "lat": min_lat,
                            "lon": min_lng
                        }
                    }
                },
            }

        if dwithin is not None:
            lng, lat = dwithin['point'].get_coords()
            kwargs['query'].setdefault('filtered', {})
            kwargs['query']['filtered'].setdefault('filter', {})
            kwargs['query']['filtered']['filter'] = {
                "geo_distance": {
                    "distance": dwithin['distance'].km,
                    dwithin['field']: {
                        "lat": lat,
                        "lon": lng
                    }
                }
            }

        # Remove the "filtered" key if we're not filtering. Otherwise,
        # Elasticsearch will blow up.
        if not kwargs['query']['filtered'].get('filter'):
            kwargs['query'] = kwargs['query']['filtered']['query']

        # Because Elasticsearch.
        query_params = {
            'from': start_offset,
        }

        if end_offset is not None and end_offset > start_offset:
            query_params['size'] = end_offset - start_offset

        try:
            raw_results = self.conn.search(None, kwargs, indexes=[self.index_name], doc_types=['modelresult'], **query_params)
        except (requests.RequestException, pyelasticsearch.ElasticSearchError), e:
            if not self.silently_fail:
                raise

            self.log.error("Failed to query Elasticsearch using '%s': %s", query_string, e)
            raw_results = {}

        return self._process_results(raw_results, highlight=highlight, result_class=result_class)

    def more_like_this(self, model_instance, additional_query_string=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=None, result_class=None, **kwargs):
        from haystack import connections

        if not self.setup_complete:
            self.setup()

        # Handle deferred models.
        if get_proxied_model and hasattr(model_instance, '_deferred') and model_instance._deferred:
            model_klass = get_proxied_model(model_instance._meta)
        else:
            model_klass = type(model_instance)

        index = connections[self.connection_alias].get_unified_index().get_index(model_klass)
        field_name = index.get_content_field()
        params = {}

        if start_offset is not None:
            params['search_from'] = start_offset

        if end_offset is not None:
            params['search_size'] = end_offset - start_offset

        doc_id = get_identifier(model_instance)

        try:
            raw_results = self.conn.morelikethis(self.index_name, 'modelresult', doc_id, [field_name], **params)
        except (requests.RequestException, pyelasticsearch.ElasticSearchError), e:
            if not self.silently_fail:
                raise

            self.log.error("Failed to fetch More Like This from Elasticsearch for document '%s': %s", doc_id, e)
            raw_results = {}

        return self._process_results(raw_results, result_class=result_class)

    def _process_results(self, raw_results, highlight=False, result_class=None):
        from haystack import connections
        results = []
        hits = raw_results.get('hits', {}).get('total', 0)
        facets = {}
        spelling_suggestion = None

        if result_class is None:
            result_class = SearchResult

        if 'facets' in raw_results:
            facets = {
                'fields': {},
                'dates': {},
                'queries': {},
            }

            for facet_fieldname, facet_info in raw_results['facets'].items():
                if facet_info.get('_type', 'terms') == 'terms':
                    facets['fields'][facet_fieldname] = [(individual['term'], individual['count']) for individual in facet_info['terms']]
                elif facet_info.get('_type', 'terms') == 'date_histogram':
                    # Elasticsearch provides UTC timestamps with an extra three
                    # decimals of precision, which datetime barfs on.
                    facets['dates'][facet_fieldname] = [(datetime.datetime.utcfromtimestamp(individual['time'] / 1000), individual['count']) for individual in facet_info['entries']]
                elif facet_info.get('_type', 'terms') == 'query':
                    facets['queries'][facet_fieldname] = facet_info['count']

        unified_index = connections[self.connection_alias].get_unified_index()
        indexed_models = unified_index.get_indexed_models()
        content_field = unified_index.document_field

        for raw_result in raw_results.get('hits', {}).get('hits', []):
            source = raw_result['_source']
            app_label, model_name = source[DJANGO_CT].split('.')
            additional_fields = {}
            model = get_model(app_label, model_name)

            if model and model in indexed_models:
                for key, value in source.items():
                    index = unified_index.get_index(model)
                    string_key = str(key)

                    if string_key in index.fields and hasattr(index.fields[string_key], 'convert'):
                        additional_fields[string_key] = index.fields[string_key].convert(value)
                    else:
                        additional_fields[string_key] = self.conn.to_python(value)

                del(additional_fields[DJANGO_CT])
                del(additional_fields[DJANGO_ID])

                if 'highlight' in raw_result:
                    additional_fields['highlighted'] = raw_result['highlight'].get(content_field, '')

                result = result_class(app_label, model_name, source[DJANGO_ID], raw_result['_score'], **additional_fields)
                results.append(result)
            else:
                hits -= 1

        return {
            'results': results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }

    def build_schema(self, fields):
        content_field_name = ''
        mapping = {}

        for field_name, field_class in fields.items():
            field_mapping = {
                'boost': field_class.boost,
                'index': 'analyzed',
                'store': 'yes',
                'type': 'string',
            }

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            # DRL_FIXME: Perhaps move to something where, if none of these
            #            checks succeed, call a custom method on the form that
            #            returns, per-backend, the right type of storage?
            if field_class.field_type in ['date', 'datetime']:
                field_mapping['type'] = 'date'
            elif field_class.field_type == 'integer':
                field_mapping['type'] = 'long'
            elif field_class.field_type == 'float':
                field_mapping['type'] = 'float'
            elif field_class.field_type == 'boolean':
                field_mapping['type'] = 'boolean'
            elif field_class.field_type == 'ngram':
                field_mapping['analyzer'] = "ngram_analyzer"
            elif field_class.field_type == 'edge_ngram':
                field_mapping['analyzer'] = "edgengram_analyzer"
            elif field_class.field_type == 'location':
                field_mapping['type'] = 'geo_point'

            # The docs claim nothing is needed for multivalue...
            # if field_class.is_multivalued:
            #     field_data['multi_valued'] = 'true'

            if field_class.stored is False:
                field_mapping['store'] = 'no'

            # Do this last to override `text` fields.
            if field_class.indexed is False or hasattr(field_class, 'facet_for'):
                field_mapping['index'] = 'not_analyzed'

            if field_mapping['type'] == 'string' and field_class.indexed:
                field_mapping["term_vector"] = "with_positions_offsets"

                if not hasattr(field_class, 'facet_for') and not field_class.field_type in('ngram', 'edge_ngram'):
                    field_mapping["analyzer"] = "snowball"

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)


# Sucks that this is almost an exact copy of what's in the Solr backend,
# but we can't import due to dependencies.
class ElasticsearchSearchQuery(BaseSearchQuery):
    def matching_all_fragment(self):
        return '*:*'

    def add_spatial(self, lat, lon, sfield, distance, filter='bbox'):
        """Adds spatial query parameters to search query"""
        kwargs = {
            'lat': lat,
            'long': long,
            'sfield': sfield,
            'distance': distance,
        }
        self.spatial_query.update(kwargs)

    def add_order_by_distance(self, lat, long, sfield):
        """Orders the search result by distance from point."""
        kwargs = {
            'lat': lat,
            'long': long,
            'sfield': sfield,
        }
        self.order_by_distance.update(kwargs)

    def build_query_fragment(self, field, filter_type, value):
        from haystack import connections
        query_frag = ''

        if not hasattr(value, 'input_type_name'):
            # Handle when we've got a ``ValuesListQuerySet``...
            if hasattr(value, 'values_list'):
                value = list(value)

            if isinstance(value, basestring):
                # It's not an ``InputType``. Assume ``Clean``.
                value = Clean(value)
            else:
                value = PythonData(value)

        # Prepare the query using the InputType.
        prepared_value = value.prepare(self)

        if not isinstance(prepared_value, (set, list, tuple)):
            # Then convert whatever we get back to what pysolr wants if needed.
            prepared_value = self.backend.conn.from_python(prepared_value)

        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        if field == 'content':
            index_fieldname = ''
        else:
            index_fieldname = u'%s:' % connections[self._using].get_unified_index().get_index_fieldname(field)

        filter_types = {
            'contains': u'%s',
            'startswith': u'%s*',
            'exact': u'%s',
            'gt': u'{%s TO *}',
            'gte': u'[%s TO *]',
            'lt': u'{* TO %s}',
            'lte': u'[* TO %s]',
        }

        if value.post_process is False:
            query_frag = prepared_value
        else:
            if filter_type in ['contains', 'startswith']:
                if value.input_type_name == 'exact':
                    query_frag = prepared_value
                else:
                    # Iterate over terms & incorportate the converted form of each into the query.
                    terms = []

                    if isinstance(prepared_value, basestring):
                        for possible_value in prepared_value.split(' '):
                            terms.append(filter_types[filter_type] % self.backend.conn.from_python(possible_value))
                    else:
                        terms.append(filter_types[filter_type] % self.backend.conn.from_python(prepared_value))

                    if len(terms) == 1:
                        query_frag = terms[0]
                    else:
                        query_frag = u"(%s)" % " AND ".join(terms)
            elif filter_type == 'in':
                in_options = []

                for possible_value in prepared_value:
                    in_options.append(u'"%s"' % self.backend.conn.from_python(possible_value))

                query_frag = u"(%s)" % " OR ".join(in_options)
            elif filter_type == 'range':
                start = self.backend.conn.from_python(prepared_value[0])
                end = self.backend.conn.from_python(prepared_value[1])
                query_frag = u'["%s" TO "%s"]' % (start, end)
            elif filter_type == 'exact':
                if value.input_type_name == 'exact':
                    query_frag = prepared_value
                else:
                    prepared_value = Exact(prepared_value).prepare(self)
                    query_frag = filter_types[filter_type] % prepared_value
            else:
                if value.input_type_name != 'exact':
                    prepared_value = Exact(prepared_value).prepare(self)

                query_frag = filter_types[filter_type] % prepared_value

        return u"%s%s" % (index_fieldname, query_frag)

    def build_alt_parser_query(self, parser_name, query_string='', **kwargs):
        if query_string:
            kwargs['v'] = query_string

        kwarg_bits = []

        for key in sorted(kwargs.keys()):
            if isinstance(kwargs[key], basestring) and ' ' in kwargs[key]:
                kwarg_bits.append(u"%s='%s'" % (key, kwargs[key]))
            else:
                kwarg_bits.append(u"%s=%s" % (key, kwargs[key]))

        return u"{!%s %s}" % (parser_name, ' '.join(kwarg_bits))

    def run(self, spelling_query=None, **kwargs):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        search_kwargs = {
            'start_offset': self.start_offset,
            'result_class': self.result_class,
        }
        order_by_list = None

        if self.order_by:
            if order_by_list is None:
                order_by_list = []


            for field in self.order_by:
                direction = 'asc'
                if field.startswith('-'):
                    direction = 'desc'
                    field = field[1:]
                order_by_list.append((field, direction))

            search_kwargs['sort_by'] = order_by_list

        if self.end_offset is not None:
            search_kwargs['end_offset'] = self.end_offset

        if self.highlight:
            search_kwargs['highlight'] = self.highlight

        if self.facets:
            search_kwargs['facets'] = list(self.facets)

        if self.date_facets:
            search_kwargs['date_facets'] = self.date_facets

        if self.query_facets:
            search_kwargs['query_facets'] = self.query_facets

        if self.narrow_queries:
            search_kwargs['narrow_queries'] = self.narrow_queries

        if self.fields:
            search_kwargs['fields'] = self.fields

        if spelling_query:
            search_kwargs['spelling_query'] = spelling_query

        if self.within:
            search_kwargs['within'] = self.within

        if self.dwithin:
            search_kwargs['dwithin'] = self.dwithin

        if self.distance_point:
            search_kwargs['distance_point'] = self.distance_point

        results = self.backend.search(final_query, **search_kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
        self._facet_counts = self.post_process_facets(results)
        self._spelling_suggestion = results.get('spelling_suggestion', None)

    def run_mlt(self, **kwargs):
        """Builds and executes the query. Returns a list of search results."""
        if self._more_like_this is False or self._mlt_instance is None:
            raise MoreLikeThisError("No instance was provided to determine 'More Like This' results.")

        additional_query_string = self.build_query()
        search_kwargs = {
            'start_offset': self.start_offset,
            'result_class': self.result_class,
        }

        if self.end_offset is not None:
            search_kwargs['end_offset'] = self.end_offset - self.start_offset

        results = self.backend.more_like_this(self._mlt_instance, additional_query_string, **search_kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)


class ElasticsearchSearchEngine(BaseEngine):
    backend = ElasticsearchSearchBackend
    query = ElasticsearchSearchQuery
