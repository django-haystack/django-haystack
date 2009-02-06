from pysolr import Solr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode
from djangosearch.backends import BaseSearchBackend, BaseSearchQuery
from djangosearch.models import SearchResult


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

    def update(self, index, iterable, commit=True):
        docs = []
        
        try:
            for obj in iterable:
                doc = {}
                doc['id'] = self.get_identifier(obj)
                doc['django_ct_s'] = "%s.%s" % (obj._meta.app_label, obj._meta.module_name)
                doc['django_id_s'] = force_unicode(obj.pk)
                
                for name, value in index.get_fields(obj):
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
        # Run an optimize post-clear. http://wiki.apache.org/solr/FAQ#head-9aafb5d8dff5308e8ea4fcf4b71f19f029c4bb99
        self.conn.optimize()

    def search(self, query_string, **kwargs):
        if len(query_string) == 0:
            return []
        
        raw_results = self.conn.search(query_string, **kwargs)
        results = []
        
        for raw_result in raw_results.docs:
            app_label, model_name = raw_result['django_ct_s'].split('.')
            result = SearchResult(app_label, model_name, raw_result['django_id_s'], raw_result['score'])
            results.append(result)
        
        return {
            'results': results,
            'hits': raw_results.hits,
        }


class SearchQuery(BaseSearchQuery):
    # DRL_FIXME: This bites. Determine how to load the above defined backend better.
    def __init__(self, backend=None):
        super(SearchQuery, self).__init__(backend=backend)
        self.backend = backend or SearchBackend()
    
    def build_query(self):
        query = ''
        
        # DRL_FIXME: Handle the other filter types.
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
                
                # Check to see if it's a phrase for an exact match.
                if ' ' in value:
                    value = '"%s"' % value
                
                # 'content' is a special reserved word, much like 'pk' in
                # Django's ORM layer. It indicates 'no special field'.
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
        
        if self.boost:
            boost_list = []
            
            for boost_word, boost_value in self.boost.items():
                boost_list.append("%s^%s" % (boost_word, boost_value))
            
            final_query = "%s %s" % (final_query, " ".join(boost_list))
        
        return final_query
    
    def clean(self, query_fragment):
        """Sanitizes a fragment from using reserved character/words."""
        cleaned = query_fragment
        
        for word in RESERVED_WORDS:
            cleaned = cleaned.replace(word, word.lower())
        
        for char in RESERVED_CHARACTERS:
            cleaned = cleaned.replace(char, '\\%s' % char)
        
        return cleaned
    
    def run(self):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = {
            'fl': '* score',
        }
        
        if self.order_by:
            order_by_list = []
            
            for ob in self.order_by:
                if order_by.startswith('-'):
                    order_by_list.append('%s asc' % '%s desc' % order_by[1:])
                else:
                    order_by_list.append('%s asc' % order_by)
            
            kwargs['sort'] = ", ".join(order_by_list)
        
        if self.start_offset:
            kwargs['start'] = self.start_offset
        
        if self.end_offset is not None:
            kwargs['rows'] = self.end_offset - self.start_offset
        
        results = self.backend.search(final_query, **kwargs)
        self._results = results.get('results', [])
        self._hit_count = results.get('hits', 0)