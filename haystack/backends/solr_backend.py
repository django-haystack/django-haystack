import logging
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.loading import get_model
from haystack.backends import BaseSearchBackend, BaseSearchQuery, log_query
from haystack.constants import ID, DJANGO_CT, DJANGO_ID
from haystack.exceptions import MissingDependency, MoreLikeThisError
from haystack.models import SearchResult
from haystack.utils import get_identifier
try:
    set
except NameError:
    from sets import Set as set
try:
    from django.db.models.sql.query import get_proxied_model
except ImportError:
    # Likely on Django 1.0
    get_proxied_model = None
try:
    from pysolr import Solr, SolrError
except ImportError:
    raise MissingDependency("The 'solr' backend requires the installation of 'pysolr'. Please refer to the documentation.")


BACKEND_NAME = 'solr'


class EmptyResults(object):
    hits = 0
    docs = []


class SearchBackend(BaseSearchBackend):
    # Word reserved by Solr for special use.
    RESERVED_WORDS = (
        'AND',
        'NOT',
        'OR',
        'TO',
    )
    
    # Characters reserved by Solr for special use.
    # The '\\' must come first, so as not to overwrite the other slash replacements.
    RESERVED_CHARACTERS = (
        '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
        '[', ']', '^', '"', '~', '*', '?', ':',
    )
    
    def __init__(self, site=None):
        super(SearchBackend, self).__init__(site)
        
        if not hasattr(settings, 'HAYSTACK_SOLR_URL'):
            raise ImproperlyConfigured('You must specify a HAYSTACK_SOLR_URL in your settings.')
        
        timeout = getattr(settings, 'HAYSTACK_SOLR_TIMEOUT', 10)
        self.conn = Solr(settings.HAYSTACK_SOLR_URL, timeout=timeout)
        self.log = logging.getLogger('haystack')
    
    def update(self, index, iterable, commit=True):
        docs = []
        
        try:
            for obj in iterable:
                docs.append(index.full_prepare(obj))
        except UnicodeDecodeError:
            sys.stderr.write("Chunk failed.\n")
        
        if len(docs) > 0:
            try:
                self.conn.add(docs, commit=commit, boost=index.get_field_weights())
            except (IOError, SolrError), e:
                self.log.error("Failed to add documents to Solr: %s", e)
    
    def remove(self, obj_or_string, commit=True):
        solr_id = get_identifier(obj_or_string)
        
        try:
            kwargs = {
                'commit': commit,
                ID: solr_id
            }
            self.conn.delete(**kwargs)
        except (IOError, SolrError), e:
            self.log.error("Failed to remove document '%s' from Solr: %s", solr_id, e)
    
    def clear(self, models=[], commit=True):
        try:
            if not models:
                # *:* matches all docs in Solr
                self.conn.delete(q='*:*', commit=commit)
            else:
                models_to_delete = []
                
                for model in models:
                    models_to_delete.append("%s:%s.%s" % (DJANGO_CT, model._meta.app_label, model._meta.module_name))
                
                self.conn.delete(q=" OR ".join(models_to_delete), commit=commit)
            
            # Run an optimize post-clear. http://wiki.apache.org/solr/FAQ#head-9aafb5d8dff5308e8ea4fcf4b71f19f029c4bb99
            self.conn.optimize()
        except (IOError, SolrError), e:
            if len(models):
                self.log.error("Failed to clear Solr index of models '%s': %s", ','.join(models_to_delete), e)
            else:
                self.log.error("Failed to clear Solr index: %s", e)
    
    @log_query
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
        if len(query_string) == 0:
            return {
                'results': [],
                'hits': 0,
            }
        
        kwargs = {
            'fl': '* score',
        }
        
        if fields:
            kwargs['fl'] = fields
        
        if sort_by is not None:
            kwargs['sort'] = sort_by
        
        if start_offset is not None:
            kwargs['start'] = start_offset
        
        if end_offset is not None:
            kwargs['rows'] = end_offset - start_offset
        
        if highlight is True:
            kwargs['hl'] = 'true'
            kwargs['hl.fragsize'] = '200'
        
        if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False) is True:
            kwargs['spellcheck'] = 'true'
            kwargs['spellcheck.collate'] = 'true'
            kwargs['spellcheck.count'] = 1
            
            if spelling_query:
                kwargs['spellcheck.q'] = spelling_query
        
        if facets is not None:
            kwargs['facet'] = 'on'
            kwargs['facet.field'] = facets
        
        if date_facets is not None:
            kwargs['facet'] = 'on'
            kwargs['facet.date'] = date_facets.keys()
            kwargs['facet.date.other'] = 'none'
            
            for key, value in date_facets.items():
                kwargs["f.%s.facet.date.start" % key] = self.conn._from_python(value.get('start_date'))
                kwargs["f.%s.facet.date.end" % key] = self.conn._from_python(value.get('end_date'))
                gap_by_string = value.get('gap_by').upper()
                gap_string = "%d%s" % (value.get('gap_amount'), gap_by_string)
                
                if value.get('gap_amount') != 1:
                    gap_string += "S"
                
                kwargs["f.%s.facet.date.gap" % key] = '+%s/%s' % (gap_string, gap_by_string)
        
        if query_facets is not None:
            kwargs['facet'] = 'on'
            kwargs['facet.query'] = ["%s:%s" % (field, value) for field, value in query_facets]
        
        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)
        
        if limit_to_registered_models:
            # Using narrow queries, limit the results to only models registered
            # with the current site.
            if narrow_queries is None:
                narrow_queries = set()
            
            registered_models = self.build_registered_models_list()
            
            if len(registered_models) > 0:
                narrow_queries.add('%s:(%s)' % (DJANGO_CT, ' OR '.join(registered_models)))
        
        if narrow_queries is not None:
            kwargs['fq'] = list(narrow_queries)
        
        try:
            raw_results = self.conn.search(query_string, **kwargs)
        except (IOError, SolrError), e:
            self.log.error("Failed to query Solr using '%s': %s", query_string, e)
            raw_results = EmptyResults()
        
        return self._process_results(raw_results, highlight=highlight, result_class=result_class)
    
    def more_like_this(self, model_instance, additional_query_string=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=None, result_class=None, **kwargs):
        # Handle deferred models.
        if get_proxied_model and hasattr(model_instance, '_deferred') and model_instance._deferred:
            model_klass = get_proxied_model(model_instance._meta)
        else:
            model_klass = type(model_instance)
        
        index = self.site.get_index(model_klass)
        field_name = index.get_content_field()
        params = {
            'fl': '*,score',
        }
        
        if start_offset is not None:
            params['start'] = start_offset
        
        if end_offset is not None:
            params['rows'] = end_offset
        
        narrow_queries = set()
        
        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)
        
        if limit_to_registered_models:
            # Using narrow queries, limit the results to only models registered
            # with the current site.
            if narrow_queries is None:
                narrow_queries = set()
            
            registered_models = self.build_registered_models_list()
            
            if len(registered_models) > 0:
                narrow_queries.add('%s:(%s)' % (DJANGO_CT, ' OR '.join(registered_models)))
        
        if additional_query_string:
            narrow_queries.add(additional_query_string)
        
        if narrow_queries:
            params['fq'] = list(narrow_queries)
        
        query = "%s:%s" % (ID, get_identifier(model_instance))
        
        try:
            raw_results = self.conn.more_like_this(query, field_name, **params)
        except (IOError, SolrError), e:
            self.log.error("Failed to fetch More Like This from Solr for document '%s': %s", query, e)
            raw_results = EmptyResults()
        
        return self._process_results(raw_results, result_class=result_class)
    
    def _process_results(self, raw_results, highlight=False, result_class=None):
        from haystack import site
        results = []
        hits = raw_results.hits
        facets = {}
        spelling_suggestion = None
        
        if result_class is None:
            result_class = SearchResult
        
        if hasattr(raw_results, 'facets'):
            facets = {
                'fields': raw_results.facets.get('facet_fields', {}),
                'dates': raw_results.facets.get('facet_dates', {}),
                'queries': raw_results.facets.get('facet_queries', {}),
            }
            
            for key in ['fields']:
                for facet_field in facets[key]:
                    # Convert to a two-tuple, as Solr's json format returns a list of
                    # pairs.
                    facets[key][facet_field] = zip(facets[key][facet_field][::2], facets[key][facet_field][1::2])
        
        if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False) is True:
            if hasattr(raw_results, 'spellcheck'):
                if len(raw_results.spellcheck.get('suggestions', [])):
                    # For some reason, it's an array of pairs. Pull off the
                    # collated result from the end.
                    spelling_suggestion = raw_results.spellcheck.get('suggestions')[-1]
        
        indexed_models = site.get_indexed_models()
        
        for raw_result in raw_results.docs:
            app_label, model_name = raw_result[DJANGO_CT].split('.')
            additional_fields = {}
            model = get_model(app_label, model_name)
            
            if model and model in indexed_models:
                for key, value in raw_result.items():
                    index = site.get_index(model)
                    string_key = str(key)
                    
                    if string_key in index.fields and hasattr(index.fields[string_key], 'convert'):
                        additional_fields[string_key] = index.fields[string_key].convert(value)
                    else:
                        additional_fields[string_key] = self.conn._to_python(value)
                
                del(additional_fields[DJANGO_CT])
                del(additional_fields[DJANGO_ID])
                del(additional_fields['score'])
                
                if raw_result[ID] in getattr(raw_results, 'highlighting', {}):
                    additional_fields['highlighted'] = raw_results.highlighting[raw_result[ID]]
                
                result = result_class(app_label, model_name, raw_result[DJANGO_ID], raw_result['score'], **additional_fields)
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
        schema_fields = []
        
        for field_name, field_class in fields.items():
            field_data = {
                'field_name': field_class.index_fieldname,
                'type': 'text',
                'indexed': 'true',
                'stored': 'true',
                'multi_valued': 'false',
            }
            
            if field_class.document is True:
                content_field_name = field_class.index_fieldname
            
            # DRL_FIXME: Perhaps move to something where, if none of these
            #            checks succeed, call a custom method on the form that
            #            returns, per-backend, the right type of storage?
            if field_class.field_type in ['date', 'datetime']:
                field_data['type'] = 'date'
            elif field_class.field_type == 'integer':
                field_data['type'] = 'slong'
            elif field_class.field_type == 'float':
                field_data['type'] = 'sfloat'
            elif field_class.field_type == 'boolean':
                field_data['type'] = 'boolean'
            elif field_class.field_type == 'ngram':
                field_data['type'] = 'ngram'
            elif field_class.field_type == 'edge_ngram':
                field_data['type'] = 'edge_ngram'
            
            if field_class.is_multivalued:
                field_data['multi_valued'] = 'true'
            
            if field_class.stored is False:
                field_data['stored'] = 'false'
            
            # Do this last to override `text` fields.
            if field_class.indexed is False:
                field_data['indexed'] = 'false'
                
                # If it's text and not being indexed, we probably don't want
                # to do the normal lowercase/tokenize/stemming/etc. dance.
                if field_data['type'] == 'text':
                    field_data['type'] = 'string'
            
            # If it's a ``FacetField``, make sure we don't postprocess it.
            if hasattr(field_class, 'facet_for'):
                # If it's text, it ought to be a string.
                if field_data['type'] == 'text':
                    field_data['type'] = 'string'
            
            schema_fields.append(field_data)
        
        return (content_field_name, schema_fields)


class SearchQuery(BaseSearchQuery):
    def __init__(self, site=None, backend=None):
        super(SearchQuery, self).__init__(site, backend)
        
        if backend is not None:
            self.backend = backend
        else:
            self.backend = SearchBackend(site=site)

    def matching_all_fragment(self):
        return '*:*'

    def build_query_fragment(self, field, filter_type, value):
        result = ''
        
        if not isinstance(value, (list, tuple)):
            # Convert whatever we find to what pysolr wants.
            value = self.backend.conn._from_python(value)
        
        # Check to see if it's a phrase for an exact match.
        if ' ' in value:
            value = '"%s"' % value
        
        index_fieldname = self.backend.site.get_index_fieldname(field)
        
        # 'content' is a special reserved word, much like 'pk' in
        # Django's ORM layer. It indicates 'no special field'.
        if field == 'content':
            result = value
        else:
            filter_types = {
                'exact': "%s:%s",
                'gt': "%s:{%s TO *}",
                'gte': "%s:[%s TO *]",
                'lt': "%s:{* TO %s}",
                'lte': "%s:[* TO %s]",
                'startswith': "%s:%s*",
            }
            
            if filter_type == 'in':
                in_options = []
                
                for possible_value in value:
                    in_options.append('%s:"%s"' % (index_fieldname, self.backend.conn._from_python(possible_value)))
                
                result = "(%s)" % " OR ".join(in_options)
            elif filter_type == 'range':
                start = self.backend.conn._from_python(value[0])
                end = self.backend.conn._from_python(value[1])
                return "%s:[%s TO %s]" % (index_fieldname, start, end)
            else:
                result = filter_types[filter_type] % (index_fieldname, value)
        
        return result
    
    def run(self, spelling_query=None):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = {
            'start_offset': self.start_offset,
            'result_class': self.result_class,
        }
        
        if self.order_by:
            order_by_list = []
            
            for order_by in self.order_by:
                if order_by.startswith('-'):
                    order_by_list.append('%s desc' % order_by[1:])
                else:
                    order_by_list.append('%s asc' % order_by)
            
            kwargs['sort_by'] = ", ".join(order_by_list)
        
        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset
        
        if self.highlight:
            kwargs['highlight'] = self.highlight
        
        if self.facets:
            kwargs['facets'] = list(self.facets)
        
        if self.date_facets:
            kwargs['date_facets'] = self.date_facets
        
        if self.query_facets:
            kwargs['query_facets'] = self.query_facets
        
        if self.narrow_queries:
            kwargs['narrow_queries'] = self.narrow_queries
        
        if spelling_query:
            kwargs['spelling_query'] = spelling_query
        
        results = self.backend.search(final_query, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
        self._facet_counts = self.post_process_facets(results)
        self._spelling_suggestion = results.get('spelling_suggestion', None)
    
    def run_mlt(self):
        """Builds and executes the query. Returns a list of search results."""
        if self._more_like_this is False or self._mlt_instance is None:
            raise MoreLikeThisError("No instance was provided to determine 'More Like This' results.")
        
        additional_query_string = self.build_query()
        kwargs = {
            'start_offset': self.start_offset,
            'result_class': self.result_class,
        }
        
        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset - self.start_offset
        
        results = self.backend.more_like_this(self._mlt_instance, additional_query_string, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
