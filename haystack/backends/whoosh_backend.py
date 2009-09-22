import os
import re
import shutil
import warnings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.loading import get_model
from django.utils.datetime_safe import datetime
from django.utils.encoding import force_unicode
from haystack.backends import BaseSearchBackend, BaseSearchQuery
from haystack.fields import DateField, DateTimeField, IntegerField, FloatField, BooleanField, MultiValueField
from haystack.exceptions import MissingDependency, SearchBackendError
from haystack.models import SearchResult
try:
    import whoosh
    from whoosh.analysis import StemmingAnalyzer
    from whoosh.fields import Schema, ID, STORED, TEXT, KEYWORD
    from whoosh import index
    from whoosh.qparser import QueryParser
    from whoosh.filedb.filestore import FileStorage
    from whoosh.spelling import SpellChecker
except ImportError:
    raise MissingDependency("The 'whoosh' backend requires the installation of 'Whoosh'. Please refer to the documentation.")

# Handle minimum requirement.
if not hasattr(whoosh, '__version__') or whoosh.__version__ < (0, 3, 0):
    raise MissingDependency("The 'whoosh' backend requires version 0.3.0 or greater.")

DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(\.\d{3,6}Z?)?$')


class SearchBackend(BaseSearchBackend):
    # Word reserved by Whoosh for special use.
    RESERVED_WORDS = (
        'AND',
        'NOT',
        'OR',
        'TO',
    )
    
    # Characters reserved by Whoosh for special use.
    # The '\\' must come first, so as not to overwrite the other slash replacements.
    RESERVED_CHARACTERS = (
        '\\', '+', '-', '&&', '||', '!', '(', ')', '{', '}',
        '[', ']', '^', '"', '~', '*', '?', ':', '.',
    )
    
    def __init__(self, site=None):
        super(SearchBackend, self).__init__(site)
        self.setup_complete = False
        
        if not hasattr(settings, 'HAYSTACK_WHOOSH_PATH'):
            raise ImproperlyConfigured('You must specify a HAYSTACK_WHOOSH_PATH in your settings.')
    
    def setup(self):
        """
        Defers loading until needed.
        """
        new_index = False
        
        # Make sure the index is there.
        if not os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            os.makedirs(settings.HAYSTACK_WHOOSH_PATH)
            new_index = True
        
        if not os.access(settings.HAYSTACK_WHOOSH_PATH, os.W_OK):
            raise IOError("The path to your Whoosh index '%s' is not writable for the current user/group." % settings.HAYSTACK_WHOOSH_PATH)
        
        self.storage = FileStorage(settings.HAYSTACK_WHOOSH_PATH)
        self.content_field_name, self.schema = self.build_schema(self.site.all_searchfields())
        self.parser = QueryParser(self.content_field_name, schema=self.schema)
        
        if new_index is True:
            self.index = index.create_in(settings.HAYSTACK_WHOOSH_PATH, self.schema)
        else:
            try:
                self.index = self.storage.open_index(schema=self.schema)
            except index.EmptyIndexError:
                self.index = index.create_in(settings.HAYSTACK_WHOOSH_PATH, self.schema)
        
        self.setup_complete = True
    
    def build_schema(self, fields):
        schema_fields = {
            'id': ID(stored=True, unique=True),
            'django_ct': ID(stored=True),
            'django_id': ID(stored=True),
        }
        # Grab the number of keys that are hard-coded into Haystack.
        # We'll use this to (possibly) fail slightly more gracefully later.
        initial_key_count = len(schema_fields)
        content_field_name = ''
        
        for field_name, field_class in fields.items():
            if isinstance(field_class, MultiValueField):
                schema_fields[field_name] = KEYWORD(stored=True, commas=True)
            elif isinstance(field_class, (DateField, DateTimeField, IntegerField, FloatField, BooleanField)):
                if field_class.indexed is False:
                    schema_fields[field_name] = STORED
                else:
                    schema_fields[field_name] = ID(stored=True)
            else:
                schema_fields[field_name] = TEXT(stored=True, analyzer=StemmingAnalyzer())
            
            if field_class.document is True:
                content_field_name = field_name
        
        # Fail more gracefully than relying on the backend to die if no fields
        # are found.
        if len(schema_fields) <= initial_key_count:
            raise SearchBackendError("No fields were found in any search_indexes. Please correct this before attempting to search.")
        
        return (content_field_name, Schema(**schema_fields))
    
    def update(self, index, iterable, commit=True):
        if not self.setup_complete:
            self.setup()
        
        self.index = self.index.refresh()
        writer = self.index.writer()
        
        for obj in iterable:
            doc = {}
            doc['id'] = force_unicode(self.get_identifier(obj))
            doc['django_ct'] = force_unicode("%s.%s" % (obj._meta.app_label, obj._meta.module_name))
            doc['django_id'] = force_unicode(obj.pk)
            other_data = index.prepare(obj)
            
            # Really make sure it's unicode, because Whoosh won't have it any
            # other way.
            for key in other_data:
                other_data[key] = self._from_python(other_data[key])
            
            doc.update(other_data)
            writer.update_document(**doc)
        
        # For now, commit no matter what, as we run into locking issues otherwise.
        writer.commit()
        
        # If spelling support is desired, add to the dictionary.
        if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False) is True:
            sp = SpellChecker(self.storage)
            sp.add_field(self.index, self.content_field_name)
    
    def remove(self, obj_or_string, commit=True):
        if not self.setup_complete:
            self.setup()
        
        self.index = self.index.refresh()
        whoosh_id = self.get_identifier(obj_or_string)
        self.index.delete_by_query(q=self.parser.parse(u'id:"%s"' % whoosh_id))
        
        # For now, commit no matter what, as we run into locking issues otherwise.
        self.index.commit()
    
    def clear(self, models=[], commit=True):
        if not self.setup_complete:
            self.setup()
        
        self.index = self.index.refresh()
        
        if not models:
            self.delete_index()
        else:
            models_to_delete = []
            
            for model in models:
                models_to_delete.append(u"django_ct:%s.%s" % (model._meta.app_label, model._meta.module_name))
            
            self.index.delete_by_query(q=self.parser.parse(u" OR ".join(models_to_delete)))
        
        # For now, commit no matter what, as we run into locking issues otherwise.
        self.index.commit()
    
    def delete_index(self):
        # Per the Whoosh mailing list, if wiping out everything from the index,
        # it's much more efficient to simply delete the index files.
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        # Recreate everything.
        self.setup()
        
    def optimize(self):
        if not self.setup_complete:
            self.setup()
        
        self.index = self.index.refresh()
        self.index.optimize()
    
    def search(self, query_string, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None, query_facets=None,
               narrow_queries=None, spelling_query=None, **kwargs):
        if not self.setup_complete:
            self.setup()
        
        # A zero length query should return no results.
        if len(query_string) == 0:
            return {
                'results': [],
                'hits': 0,
            }
        
        query_string = force_unicode(query_string)
        
        # A one-character query (non-wildcard) gets nabbed by a stopwords
        # filter and should yield zero results.
        if len(query_string) <= 1 and query_string != u'*':
            return {
                'results': [],
                'hits': 0,
            }
        
        reverse = False
        
        if sort_by is not None:
            # Determine if we need to reverse the results and if Whoosh can
            # handle what it's being asked to sort by. Reversing is an
            # all-or-nothing action, unfortunately.
            sort_by_list = []
            reverse_counter = 0
            
            for order_by in sort_by:
                if order_by.startswith('-'):
                    reverse_counter += 1
            
            if len(sort_by) > 1 and reverse_counter > 1:
                raise SearchBackendError("Whoosh does not handle more than one field and any field being ordered in reverse.")
            
            for order_by in sort_by:
                if order_by.startswith('-'):
                    sort_by_list.append(order_by[1:])
                    
                    if len(sort_by_list) == 1:
                        reverse = True
                else:
                    sort_by_list.append(order_by)
                    
                    if len(sort_by_list) == 1:
                        reverse = False
                
            sort_by = sort_by_list[0]
        
        if facets is not None:
            warnings.warn("Whoosh does not handle faceting.", Warning, stacklevel=2)
        
        if date_facets is not None:
            warnings.warn("Whoosh does not handle date faceting.", Warning, stacklevel=2)
        
        if query_facets is not None:
            warnings.warn("Whoosh does not handle query faceting.", Warning, stacklevel=2)
        
        narrowed_results = None
        self.index = self.index.refresh()
        
        if narrow_queries is not None:
            # Potentially expensive? I don't see another way to do it in Whoosh...
            narrow_searcher = self.index.searcher()
            
            for nq in narrow_queries:
                recent_narrowed_results = narrow_searcher.search(self.parser.parse(force_unicode(nq)))
                
                if narrowed_results:
                    narrowed_results.filter(recent_narrowed_results)
                else:
                   narrowed_results = recent_narrowed_results
        
        self.index = self.index.refresh()
        
        if self.index.doc_count():
            searcher = self.index.searcher()
            parsed_query = self.parser.parse(query_string)
            
            # In the event of an invalid/stopworded query, recover gracefully.
            if parsed_query is None:
                return {
                    'results': [],
                    'hits': 0,
                }
            
            # DRL_TODO: Ignoring offsets for now, as slicing caused issues with pagination.
            raw_results = searcher.search(parsed_query, sortedby=sort_by, reverse=reverse)
            
            # Handle the case where the results have been narrowed.
            if narrowed_results:
                raw_results.filter(narrowed_results)
            
            return self._process_results(raw_results, highlight=highlight, query_string=query_string)
        else:
            if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False):
                if spelling_query:
                    spelling_suggestion = self.create_spelling_suggestion(spelling_query)
                else:
                    spelling_suggestion = self.create_spelling_suggestion(query_string)
            else:
                spelling_suggestion = None
            
            return {
                'results': [],
                'hits': 0,
                'spelling_suggestion': spelling_suggestion,
            }
    
    def more_like_this(self, model_instance, additional_query_string=None):
        warnings.warn("Whoosh does not handle More Like This.", Warning, stacklevel=2)
        return {
            'results': [],
            'hits': 0,
        }
    
    def _process_results(self, raw_results, highlight=False, query_string=''):
        from haystack import site
        results = []
        hits = len(raw_results)
        facets = {}
        spelling_suggestion = None
        indexed_models = site.get_indexed_models()
        
        for doc_offset, raw_result in enumerate(raw_results):
            raw_result = dict(raw_result)
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
                        additional_fields[string_key] = self._to_python(value)
                
                del(additional_fields['django_ct'])
                del(additional_fields['django_id'])
                
                if highlight:
                    from whoosh import analysis
                    from whoosh.highlight import highlight, ContextFragmenter, UppercaseFormatter
                    sa = analysis.StemmingAnalyzer()
                    terms = [term.replace('*', '') for term in query_string.split()]
                    
                    # DRL_FIXME: Highlighting doesn't seem to work properly in testing.
                    additional_fields['highlighted'] = {
                        self.content_field_name: [highlight(additional_fields.get(self.content_field_name), terms, sa, ContextFragmenter(terms), UppercaseFormatter())],
                    }
                
                # Requires Whoosh 0.1.20+.
                if hasattr(raw_results, 'score'):
                    score = raw_results.score(doc_offset)
                else:
                    score = None
                
                if score is None:
                    score = 0
                
                result = SearchResult(app_label, model_name, raw_result['django_id'], score, **additional_fields)
                results.append(result)
            else:
                hits -= 1
        
        if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False) is True:
            spelling_suggestion = self.create_spelling_suggestion(query_string)
        
        return {
            'results': results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }
    
    def create_spelling_suggestion(self, query_string):
        spelling_suggestion = None
        sp = SpellChecker(self.storage)
        cleaned_query = query_string
        
        if not query_string:
            return spelling_suggestion
        
        # Clean the string.
        for rev_word in self.RESERVED_WORDS:
            cleaned_query = cleaned_query.replace(rev_word, '')
        
        for rev_char in self.RESERVED_CHARACTERS:
            cleaned_query = cleaned_query.replace(rev_char, '')
        
        # Break it down.
        query_words = cleaned_query.split()
        suggested_words = []
        
        for word in query_words:
            suggestions = sp.suggest(word, number=1)
            
            if len(suggestions) > 0:
                suggested_words.append(suggestions[0])
        
        spelling_suggestion = ' '.join(suggested_words)
        return spelling_suggestion
    
    def _from_python(self, value):
        """
        Converts Python values to a string for Whoosh.
        
        Code courtesy of pysolr.
        """
        if hasattr(value, 'strftime'):
            if hasattr(value, 'hour'):
                value = force_unicode(value.strftime('%Y-%m-%dT%H:%M:%S'))
            else:
                value = force_unicode(value.strftime('%Y-%m-%dT00:00:00'))
        elif isinstance(value, bool):
            if value:
                value = u'true'
            else:
                value = u'false'
        else:
            value = force_unicode(value)
        return value
    
    def _to_python(self, value):
        """
        Converts values from Whoosh to native Python values.
        
        A port of the same method in pysolr, as they deal with data the same way.
        """
        if value == 'true':
            return True
        elif value == 'false':
            return False
        
        if value:
            possible_datetime = DATETIME_REGEX.search(value)
            
            if possible_datetime:
                date_values = possible_datetime.groupdict()
            
                for dk, dv in date_values.items():
                    date_values[dk] = int(dv)
            
                return datetime(date_values['year'], date_values['month'], date_values['day'], date_values['hour'], date_values['minute'], date_values['second'])
        
        try:
            # This is slightly gross but it's hard to tell otherwise what the
            # string's original type might have been. Be careful who you trust.
            converted_value = eval(value)
            
            # Try to handle most built-in types.
            if isinstance(converted_value, (list, tuple, set, dict, int, float, long, complex)):
                return converted_value
        except:
            # If it fails (SyntaxError or its ilk) or we don't trust it,
            # continue on.
            pass
        
        return value


class SearchQuery(BaseSearchQuery):
    def __init__(self, backend=None):
        super(SearchQuery, self).__init__(backend=backend)
        self.backend = backend or SearchBackend()
    
    def build_query(self):
        query = u''
        
        if not self.query_filters:
            # Match all.
            query = u'*'
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
                
                if the_filter.filter_type != 'in':
                    # 'in' is a bit of a special case, as we don't want to
                    # convert a valid list/tuple to string. Defer handling it
                    # until later...
                    value = self.backend._from_python(value)
                
                # Check to see if it's a phrase for an exact match.
                if ' ' in value:
                    value = '"%s"' % value
                
                # 'content' is a special reserved word, much like 'pk' in
                # Django's ORM layer. It indicates 'no special field'.
                if the_filter.field == 'content':
                    query_chunks.append(value)
                else:
                    filter_types = {
                        'exact': "%s:%s",
                        'gt': "%s:{%s TO}",
                        'gte': "%s:[%s TO]",
                        'lt': "%s:{TO %s}",
                        'lte': "%s:[TO %s]",
                        'startswith': "%s:%s*",
                    }
                    
                    if the_filter.filter_type != 'in':
                        possible_datetime = DATETIME_REGEX.search(value)
                        
                        if possible_datetime:
                            value = self.clean(value)
                        
                        query_chunks.append(filter_types[the_filter.filter_type] % (the_filter.field, value))
                    else:
                        in_options = []
                        
                        for possible_value in value:
                            pv = self.backend._from_python(possible_value)
                            possible_datetime = DATETIME_REGEX.search(pv)
                            
                            if possible_datetime:
                                pv = self.clean(pv)
                            
                            in_options.append('%s:"%s"' % (the_filter.field, pv))
                        
                        query_chunks.append("(%s)" % " OR ".join(in_options))
            
            if query_chunks[0] in ('AND', 'OR'):
                # Pull off an undesirable leading "AND" or "OR".
                del(query_chunks[0])
            
            query = u" ".join(query_chunks)
        
        if len(self.models):
            models = ['django_ct:"%s.%s"' % (model._meta.app_label, model._meta.module_name) for model in self.models]
            models_clause = ' OR '.join(models)
            final_query = u'(%s) AND (%s)' % (query, models_clause)
        else:
            final_query = query
        
        if self.boost:
            boost_list = []
            
            for boost_word, boost_value in self.boost.items():
                boost_list.append("%s^%s" % (boost_word, boost_value))
            
            final_query = u"%s %s" % (final_query, " ".join(boost_list))
        
        return final_query
    
    def run(self, spelling_query=None):
        """Builds and executes the query. Returns a list of search results."""
        final_query = self.build_query()
        kwargs = {
            'start_offset': self.start_offset,
        }
        
        if self.order_by:
            kwargs['sort_by'] = self.order_by
        
        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset - self.start_offset
        
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
