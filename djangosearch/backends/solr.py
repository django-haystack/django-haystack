from pysolr import Solr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode
from djangosearch.backends import BaseSearchBackend, BaseSearchQuery
from djangosearch.models import SearchResult


# DRL_FIXME: Get clarification on the comment below.
# TODO: Support for using Solr dynnamicField declarations, the magic fieldname
# postfixes like _i for integers. Requires some sort of global field registry
# though. Is it even worth it?


class SearchBackend(BaseSearchBackend):
    def __init__(self):
        if not hasattr(settings, 'SOLR_URL'):
            raise ImproperlyConfigured('You must specify a SOLR_URL in your settings.')
        
        # DRL_TODO: This should handle the connection more graceful, especially
        #           if the backend is down.
        self.conn = Solr(settings.SOLR_URL)

    def update(self, indexer, iterable, commit=True):
        docs = []
        try:
            for obj in iterable:
                doc = {}
                doc['id'] = self.get_identifier(obj)
                doc['django_ct_s'] = "%s.%s" % (obj._meta.app_label, obj._meta.module_name)
                doc['django_id_s'] = force_unicode(obj.pk)
                doc['text'] = indexer.flatten(obj)
                for name, value in indexer.get_indexed_fields(obj):
                    doc[name] = value
                docs.append(doc)
        except UnicodeDecodeError:
            print "Chunk failed."
            pass
        self.conn.add(docs, commit=commit)

    def remove(self, obj, commit=True):
        solr_id = self.get_identifier(obj)
        self.conn.delete(id=solr_id, commit=commit)

    def clear(self, models, commit=True):
        # *:* matches all docs in Solr
        self.conn.delete(q='*:*', commit=commit)

    def search(self, query_string):
        if len(query_string) == 0:
            return []
        
        raw_results = self.conn.search(query_string)
        results = []
        
        for raw_result in raw_results.docs:
            app_label, model_name = raw_result['django_ct_s'].split('.')
            result = SearchResult(app_label, model_name, result['django_id_s'], result['score'])
            results.append(result)
        
        # DRL_TODO: Do we want a class here instead? I don't think so (as
        #           there's no behavior to go with it).
        return {
            'results': results,
            'hits': raw_results.hits,
        }


class SearchQuery(BaseSearchQuery):
    def build_query(self):
        query = ''
        
        # DRL_FIXME: Handle the filters.
        if not self.query_filters:
            # Match all.
            query = '*:*'
        else:
            query_chunks = []
            
            for the_filter in self.query_filters:
                if the_filter.is_and():
                    query_chunks.append('AND')
                
                if the_filter.is_not():
                    query_chunks.append('NOT')
                
                if the_filter.is_or():
                    query_chunks.append('OR')
                
                value = the_filter.value
                
                if ' ' in value:
                    value = "'%s'" % value
                
                if the_filter.field == 'content':
                    query_chunks.append(value)
                else:
                    query_chunks.append("%s:%s" % (the_filter.field, value))
            
            if query_chunks[0] in ('AND', 'OR'):
                # Pull off an undesirable leading "AND" or "OR".
                del(query_chunks[0])
            
            query = " ".join(query_chunks)
        
        if len(self.models):
            models = ['django_ct_s:"%s.%s"' % (model._meta.app_label, model._meta.module_name) for model in self.models]
            models_clause = ' OR '.join(models)
            final_query = '(%s) AND (%s)' % (query, models_clause)
        else:
            final_query = query
        
        # DRL_FIXME: Handle boost.
        
        return final_query
    
    def clean(self, query_fragment):
        # DRL_FIXME: Not sure what characters are invalid/reserved.
        pass
    
    def run(self):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = {
            'fl': '*,score',
        }
        
        if self.order_by:
            # DRL_FIXME: From the looks of the docs, maybe we can have multiple
            #            order_by's (like our API supports).
            order_by = self.order_by[0]
            
            if order_by.startswith('-'):
                kwargs['sort'] = '%s desc' % order_by[1:]
            else:
                kwargs['sort'] = '%s asc' % order_by
        
        if self.start_offset:
            kwargs['start'] = self.start_offset
        
        if self.end_offset is not None:
            kwargs['rows'] = self.end_offset - self.start_offset
        
        results = self.backend.search(final_query, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)