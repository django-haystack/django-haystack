from pysolr import Solr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode
from djangosearch.backends import SearchEngine as BaseSearchEngine
from djangosearch.backends import BaseSearchQuery


# DRL_FIXME: Get clarification on the comment below.
# TODO: Support for using Solr dynnamicField declarations, the magic fieldname
# postfixes like _i for integers. Requires some sort of global field registry
# though. Is it even worth it?


class SearchEngine(BaseSearchEngine):
    def __init__(self):
        if not hasattr(settings, 'SOLR_URL'):
            raise ImproperlyConfigured('You must specify a SOLR_URL in your settings.')
        
        # DRL_TODO: This should handle the connection more graceful, especially
        #           if the backend is down.
        self.conn = Solr(settings.SOLR_URL)

    def _models_query(self, models):
        def qt(model):
            return 'django_ct_s:"%s.%s"' % (model._meta.app_label, model._meta.module_name)
        return ' OR '.join([qt(model) for model in models])

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
    
    # DRL_FIXME: Remove?
    def _result_callback(self, result):
        app_label, model_name = result['django_ct_s'].split('.')
        return (app_label, model_name, result['django_id_s'], None)

    def search(self, query_string):
        if len(query_string) == 0:
            return []
        
        results = self.conn.search(query_string)
        # DRL_TODO: Do we want a class here instead? I don't think so (as
        #           there's no behavior to go with it).
        return {
            'results': iter(results.docs),
            'hits': results.hits,
        }


class SearchQuery(BaseSearchQuery):
    def get_count(self):
        pass
    
    def build_query(self):
        # Old Implementation.
        # original_query = q
        # 
        # if models is not None:
        #     models_clause = self._models_query(models)
        #     final_q = '(%s) AND (%s)' % (q, models_clause)
        # else:
        #     final_q = q
        # 
        # kwargs = {}
        # if order_by != RELEVANCE:
        #     if order_by[0] == '-':
        #         kwargs['sort'] = '%s desc' % order_by[1:]
        #     else:
        #         kwargs['sort'] = '%s asc' % order_by
        # 
        # if limit is not None:
        #     kwargs['rows'] = limit
        # if offset is not None:
        #     kwargs['start'] = offset
        pass
    
    def clean(self, query_fragment):
        pass
