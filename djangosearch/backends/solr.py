from datetime import datetime, date
from pysolr import Solr
from django.conf import settings
from django.utils.encoding import force_unicode
from djangosearch.query import RELEVANCE, QueryConverter, convert as convert_query
from djangosearch.results import SearchResults
from djangosearch.backends.base import SearchEngine as BaseSearchEngine


# TODO: Support for using Solr dynnamicField declarations, the magic fieldname
# postfixes like _i for integers. Requires some sort of global field registry
# though. Is it even worth it?

class SearchEngine(BaseSearchEngine):
    def __init__(self):
        args = [settings.SOLR_URL]
        self.conn = Solr(*args)

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

    def _result_callback(self, result):
        app_label, model_name = result['django_ct_s'].split('.')
        return (app_label, model_name, result['django_id_s'], None)

    def search(self, q, models=None, order_by=RELEVANCE, limit=None, offset=None):
        if len(q) == 0:
            return SearchResults(q, [], 0, lambda x: x)
        original_query = q
        q = convert_query(original_query, SolrQueryConverter)

        if models is not None:
            models_clause = self._models_query(models)
            final_q = '(%s) AND (%s)' % (q, models_clause)
        else:
            final_q = q

        kwargs = {}
        if order_by != RELEVANCE:
            if order_by[0] == '-':
                kwargs['sort'] = '%s desc' % order_by[1:]
            else:
                kwargs['sort'] = '%s asc' % order_by

        if limit is not None:
            kwargs['rows'] = limit
        if offset is not None:
            kwargs['start'] = offset

        results = self.conn.search(final_q, **kwargs)
        return SearchResults(final_q, iter(results.docs), results.hits, self._result_callback)

class SolrQueryConverter(QueryConverter):
    QUOTES          = '""'
    GROUPERS        = "()"
    OR              = " "
    NOT             = "NOT "
    SEPARATOR       = ' AND '
    FIELDSEP        = ':'
