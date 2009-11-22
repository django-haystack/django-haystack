import logging
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.loading import get_model
from django.db.models.sql.query import get_proxied_model
from django.utils.encoding import force_unicode
from haystack.backends import BaseSearchBackend, BaseSearchQuery, log_query
from haystack.exceptions import MissingDependency, MoreLikeThisError
from haystack.fields import DateField, DateTimeField, IntegerField, FloatField, BooleanField, MultiValueField
from haystack.models import SearchResult
from haystack.utils import get_identifier
try:
    set
except NameError:
    from sets import Set as set
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
                docs.append(index.prepare(obj))
        except UnicodeDecodeError:
            sys.stderr.write("Chunk failed.\n")
        
        if len(docs) > 0:
            try:
                self.conn.add(docs, commit=commit)
            except (IOError, SolrError), e:
                self.log.error("Failed to add documents to Solr: %s", e)
    
    def remove(self, obj_or_string, commit=True):
        solr_id = get_identifier(obj_or_string)
        
        try:
            self.conn.delete(id=solr_id, commit=commit)
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
                    models_to_delete.append("django_ct:%s.%s" % (model._meta.app_label, model._meta.module_name))
                
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
               limit_to_registered_models=True, **kwargs):
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
            
            for key, value in date_facets.items():
                # Date-based facets in Solr kinda suck.
                kwargs["f.%s.facet.date.start" % key] = self.conn._from_python(value.get('start_date'))
                kwargs["f.%s.facet.date.end" % key] = self.conn._from_python(value.get('end_date'))
                gap_string = value.get('gap_by').upper()
                
                if value.get('gap_amount') != 1:
                    gap_string = "%d%sS" % (value.get('gap_amount'), gap_string)
                
                kwargs["f.%s.facet.date.gap" % key] = "/%s" % gap_string
        
        if query_facets is not None:
            kwargs['facet'] = 'on'
            kwargs['facet.query'] = ["%s:%s" % (field, value) for field, value in query_facets.items()]
        
        if limit_to_registered_models:
            # Using narrow queries, limit the results to only models registered
            # with the current site.
            if narrow_queries is None:
                narrow_queries = set()
            
            registered_models = self.build_registered_models_list()
            
            if len(registered_models) > 0:
                narrow_queries.add('django_ct:(%s)' % ' OR '.join(registered_models))
        
        if narrow_queries is not None:
            kwargs['fq'] = list(narrow_queries)
        
        try:
            raw_results = self.conn.search(query_string, **kwargs)
        except (IOError, SolrError), e:
            self.log.error("Failed to query Solr using '%s': %s", query_string, e)
            raw_results = EmptyResults()
        
        return self._process_results(raw_results, highlight=highlight)
    
    def more_like_this(self, model_instance, additional_query_string=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=True, **kwargs):
        # Handle deferred models.
        if hasattr(model_instance, '_deferred') and model_instance._deferred:
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
        
        if limit_to_registered_models:
            # Using narrow queries, limit the results to only models registered
            # with the current site.
            if narrow_queries is None:
                narrow_queries = set()
            
            registered_models = self.build_registered_models_list()
            
            if len(registered_models) > 0:
                narrow_queries.add('django_ct:(%s)' % ' OR '.join(registered_models))
        
        if additional_query_string:
            narrow_queries.add(additional_query_string)
        
        if narrow_queries:
            params['fq'] = list(narrow_queries)
        
        query = "id:%s" % get_identifier(model_instance)
        
        try:
            raw_results = self.conn.more_like_this(query, field_name, **params)
        except (IOError, SolrError), e:
            self.log.error("Failed to fetch More Like This from Solr for document '%s': %s", query, e)
            raw_results = EmptyResults()
        
        return self._process_results(raw_results)
    
    def _process_results(self, raw_results, highlight=False):
        from haystack import site
        results = []
        hits = raw_results.hits
        facets = {}
        spelling_suggestion = None
        
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
            app_label, model_name = raw_result['django_ct'].split('.')
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
                
                del(additional_fields['django_ct'])
                del(additional_fields['django_id'])
                del(additional_fields['score'])
                
                if raw_result['id'] in getattr(raw_results, 'highlighting', {}):
                    additional_fields['highlighted'] = raw_results.highlighting[raw_result['id']]
                
                result = SearchResult(app_label, model_name, raw_result['django_id'], raw_result['score'], **additional_fields)
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
                'field_name': field_name,
                'type': 'text',
                'indexed': 'true',
                'multi_valued': 'false',
            }
            
            if field_class.document is True:
                content_field_name = field_name
            
            # DRL_FIXME: Perhaps move to something where, if none of these
            #            checks succeed, call a custom method on the form that
            #            returns, per-backend, the right type of storage?
            # DRL_FIXME: Also think about removing `isinstance` and replacing
            #            it with a method call/string returned (like 'text' or
            #            'date').
            if isinstance(field_class, (DateField, DateTimeField)):
                field_data['type'] = 'date'
            elif isinstance(field_class, IntegerField):
                field_data['type'] = 'slong'
            elif isinstance(field_class, FloatField):
                field_data['type'] = 'sfloat'
            elif isinstance(field_class, BooleanField):
                field_data['type'] = 'boolean'
            elif isinstance(field_class, MultiValueField):
                field_data['multi_valued'] = 'true'
            
            # Do this last to override `text` fields.
            if field_class.indexed is False:
                field_data['indexed'] = 'false'
                
                # If it's text and not being indexed, we probably don't want
                # to do the normal lowercase/tokenize/stemming/etc. dance.
                if field_data['type'] == 'text':
                    field_data['type'] = 'string'
            
            schema_fields.append(field_data)
        
        return (content_field_name, schema_fields)


class SearchQuery(BaseSearchQuery):
    def __init__(self, backend=None):
        super(SearchQuery, self).__init__(backend=backend)
        self.backend = backend or SearchBackend()

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
            
            if filter_type != 'in':
                result = filter_types[filter_type] % (field, value)
            else:
                in_options = []
                
                for possible_value in value:
                    in_options.append('%s:"%s"' % (field, self.backend.conn._from_python(possible_value)))
                
                result = "(%s)" % " OR ".join(in_options)
        
        return result
    
    def run(self, spelling_query=None):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = {
            'start_offset': self.start_offset,
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
        self._facet_counts = results.get('facets', {})
        self._spelling_suggestion = results.get('spelling_suggestion', None)
    
    def run_mlt(self):
        """Builds and executes the query. Returns a list of search results."""
        if self._more_like_this is False or self._mlt_instance is None:
            raise MoreLikeThisError("No instance was provided to determine 'More Like This' results.")
        
        additional_query_string = self.build_query()
        kwargs = {
            'start_offset': self.start_offset,
        }
        
        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset - self.start_offset
        
        results = self.backend.more_like_this(self._mlt_instance, additional_query_string, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)
