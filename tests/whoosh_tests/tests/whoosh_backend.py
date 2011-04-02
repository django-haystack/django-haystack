from datetime import timedelta
import os
import shutil
from whoosh.fields import TEXT, KEYWORD, NUMERIC, DATETIME, BOOLEAN
from whoosh.qparser import QueryParser
from django.conf import settings
from django.utils.datetime_safe import datetime, date
from django.test import TestCase
from haystack import backends
from haystack import indexes
from haystack.backends.whoosh_backend import SearchBackend, SearchQuery
from haystack.models import SearchResult
from haystack.query import SearchQuerySet, SQ
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel
from core.tests.mocks import MockSearchResult
try:
    set
except NameError:
    from sets import Set as set


class WhooshMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')


class AllTypesWhooshMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', indexed=False)
    pub_date = indexes.DateField(model_attr='pub_date')
    sites = indexes.MultiValueField()
    seen_count = indexes.IntegerField(indexed=False)
    is_active = indexes.BooleanField(default=True)


class WhooshMaintainTypeMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateField(model_attr='pub_date')
    
    def prepare_text(self, obj):
        return "Indexed!\n%s" % obj.pk
    
    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month


class WhooshAutocompleteMockModelSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')
    text_auto = indexes.EdgeNgramField(model_attr='foo')
    name_auto = indexes.EdgeNgramField(model_attr='author')


class WhooshSearchBackendTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(WhooshSearchBackendTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.wmtmmi = WhooshMaintainTypeMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        # With the models registered, you get the proper bits.
        import haystack
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.sb.delete_index()
        
        self.sample_objs = MockModel.objects.all()
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        
        # Restore.
        import haystack
        haystack.site = self.old_site
        
        super(WhooshSearchBackendTestCase, self).tearDown()
    
    def whoosh_search(self, query):
        self.raw_whoosh = self.raw_whoosh.refresh()
        searcher = self.raw_whoosh.searcher()
        return searcher.search(self.parser.parse(query), limit=1000)
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Whoosh thinks is there.
        self.assertEqual(len(self.whoosh_search(u'*')), 23)
        self.assertEqual([doc.fields()['id'] for doc in self.whoosh_search(u'*')], [u'core.mockmodel.%s' % i for i in xrange(1, 24)])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.sb.index.doc_count(), 23)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.sb.index.doc_count(), 22)
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.sb.index.doc_count(), 23)
        
        self.sb.clear()
        self.assertEqual(self.sb.index.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.sb.index.doc_count(), 23)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(self.sb.index.doc_count(), 23)
        
        self.sb.clear([MockModel])
        self.assertEqual(self.sb.index.doc_count(), 0)
        
        self.sb.index.refresh()
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.sb.index.doc_count(), 23)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 23)
        
        # No query string should always yield zero results.
        self.assertEqual(self.sb.search(u''), {'hits': 0, 'results': []})
        
        # A one letter query string gets nabbed by a stopwords filter. Should
        # always yield zero results.
        self.assertEqual(self.sb.search(u'a'), {'hits': 0, 'results': []})
        
        # Possible AttributeError?
        # self.assertEqual(self.sb.search(u'a b'), {'hits': 0, 'results': [], 'spelling_suggestion': '', 'facets': {}})
        
        self.assertEqual(self.sb.search(u'*')['hits'], 23)
        self.assertEqual([result.pk for result in self.sb.search(u'*')['results']], [u'%s' % i for i in xrange(1, 24)])
        
        self.assertEqual(self.sb.search(u'', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search(u'index*', highlight=True)['hits'], 23)
        # DRL_FIXME: Uncomment once highlighting works.
        # self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index*', highlight=True)['results']], ['<em>Indexed</em>!\n3', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n1'])
        
        self.assertEqual(self.sb.search(u'Indx')['hits'], 0)
        self.assertEqual(self.sb.search(u'Indx')['spelling_suggestion'], u'index')
        
        self.assertEqual(self.sb.search(u'', facets=['name']), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', facets=['name'])
        results = self.sb.search(u'index*', facets=['name'])
        self.assertEqual(results['hits'], 23)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search(u'', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}}), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}})
        results = self.sb.search(u'index*', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}})
        self.assertEqual(results['hits'], 23)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search(u'', query_facets={'name': '[* TO e]'}), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', query_facets={'name': '[* TO e]'})
        results = self.sb.search(u'index*', query_facets={'name': '[* TO e]'})
        self.assertEqual(results['hits'], 23)
        self.assertEqual(results['facets'], {})
        
        # self.assertEqual(self.sb.search('', narrow_queries=set(['name:daniel1'])), {'hits': 0, 'results': []})
        # results = self.sb.search('Index*', narrow_queries=set(['name:daniel1']))
        # self.assertEqual(results['hits'], 1)
        
        # Ensure that swapping the ``result_class`` works.
        self.assertTrue(isinstance(self.sb.search(u'Index*', result_class=MockSearchResult)['results'][0], MockSearchResult))
        
        # Check the use of ``limit_to_registered_models``.
        self.assertEqual(self.sb.search(u'', limit_to_registered_models=False), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search(u'*', limit_to_registered_models=False)['hits'], 23)
        self.assertEqual([result.pk for result in self.sb.search(u'*', limit_to_registered_models=False)['results']], [u'%s' % i for i in xrange(1, 24)])
        
        # Stow.
        old_limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False
        
        self.assertEqual(self.sb.search(u''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search(u'*')['hits'], 23)
        self.assertEqual([result.pk for result in self.sb.search(u'*')['results']], [u'%s' % i for i in xrange(1, 24)])
        
        # Restore.
        settings.HAYSTACK_LIMIT_TO_REGISTERED_MODELS = old_limit_to_registered_models
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 23)
        
        # Unsupported by Whoosh. Should see empty results.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
        
        # Make sure that swapping the ``result_class`` doesn't blow up.
        try:
            self.sb.search(u'index document', result_class=MockSearchResult)
        except:
            self.fail()
    
    def test_delete_index(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        self.sb.delete_index()
        self.assertEqual(self.sb.index.doc_count(), 0)
    
    def test_order_by(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        results = self.sb.search(u'*', sort_by=['pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'1', u'3', u'2', u'4', u'5', u'6', u'7', u'8', u'9', u'10', u'11', u'12', u'13', u'14', u'15', u'16', u'17', u'18', u'19', u'20', u'21', u'22', u'23'])
        
        results = self.sb.search(u'*', sort_by=['-pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'23', u'22', u'21', u'20', u'19', u'18', u'17', u'16', u'15', u'14', u'13', u'12', u'11', u'10', u'9', u'8', u'7', u'6', u'5', u'4', u'2', u'3', u'1'])
        
        results = self.sb.search(u'*', sort_by=['id'])
        self.assertEqual([result.pk for result in results['results']], [u'1', u'10', u'11', u'12', u'13', u'14', u'15', u'16', u'17', u'18', u'19', u'2', u'20', u'21', u'22', u'23', u'3', u'4', u'5', u'6', u'7', u'8', u'9'])
        
        results = self.sb.search(u'*', sort_by=['-id'])
        self.assertEqual([result.pk for result in results['results']], [u'9', u'8', u'7', u'6', u'5', u'4', u'3', u'23', u'22', u'21', u'20', u'2', u'19', u'18', u'17', u'16', u'15', u'14', u'13', u'12', u'11', u'10', u'1'])
    
    def test__from_python(self):
        self.assertEqual(self.sb._from_python('abc'), u'abc')
        self.assertEqual(self.sb._from_python(1), 1)
        self.assertEqual(self.sb._from_python(2653), 2653)
        self.assertEqual(self.sb._from_python(25.5), 25.5)
        self.assertEqual(self.sb._from_python([1, 2, 3]), u'1,2,3')
        self.assertEqual(self.sb._from_python({'a': 1, 'c': 3, 'b': 2}), u"{'a': 1, 'c': 3, 'b': 2}")
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 9, 16, 14)), datetime(2009, 5, 9, 16, 14))
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 9, 0, 0)), datetime(2009, 5, 9, 0, 0))
        self.assertEqual(self.sb._from_python(datetime(1899, 5, 18, 0, 0)), datetime(1899, 5, 18, 0, 0))
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 18, 1, 16, 30, 250)), datetime(2009, 5, 18, 1, 16, 30, 250))
    
    def test__to_python(self):
        self.assertEqual(self.sb._to_python('abc'), 'abc')
        self.assertEqual(self.sb._to_python('1'), 1)
        self.assertEqual(self.sb._to_python('2653'), 2653)
        self.assertEqual(self.sb._to_python('25.5'), 25.5)
        self.assertEqual(self.sb._to_python('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(self.sb._to_python('{"a": 1, "b": 2, "c": 3}'), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(self.sb._to_python('2009-05-09T16:14:00'), datetime(2009, 5, 9, 16, 14))
        self.assertEqual(self.sb._to_python('2009-05-09T00:00:00'), datetime(2009, 5, 9, 0, 0))
        self.assertEqual(self.sb._to_python(None), None)
    
    def test_range_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u'[d TO]')), 23)
        self.assertEqual(len(self.whoosh_search(u'name:[d TO]')), 23)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND name:[d to]')), 23)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND name:[to c]')), 0)
    
    def test_date_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u"pub_date:20090717003000")), 1)
        self.assertEqual(len(self.whoosh_search(u"pub_date:20090717000000")), 0)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND pub_date:[to 20090717003000]')), 3)
    
    def test_escaped_characters_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u"Indexed\!")), 23)
        self.assertEqual(len(self.whoosh_search(u"http\:\/\/www\.example\.com")), 0)
    
    def test_build_schema(self):
        self.site.unregister(MockModel)
        self.site.register(MockModel, AllTypesWhooshMockSearchIndex)
        
        (content_field_name, schema) = self.sb.build_schema(self.site.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(schema.names()), 9)
        self.assertEqual(schema.names(), ['django_ct', 'django_id', 'id', 'is_active', 'name', 'pub_date', 'seen_count', 'sites', 'text'])
        self.assert_(isinstance(schema._fields['text'], TEXT))
        self.assert_(isinstance(schema._fields['pub_date'], DATETIME))
        self.assert_(isinstance(schema._fields['seen_count'], NUMERIC))
        self.assert_(isinstance(schema._fields['sites'], KEYWORD))
        self.assert_(isinstance(schema._fields['is_active'], BOOLEAN))
    
    def test_verify_type(self):
        import haystack
        haystack.site.unregister(MockModel)
        haystack.site.register(MockModel, WhooshMaintainTypeMockSearchIndex)
        self.sb.setup()
        self.sb.update(self.wmtmmi, self.sample_objs)
        
        self.assertEqual(self.sb.search(u'*')['hits'], 23)
        self.assertEqual([result.month for result in self.sb.search(u'*')['results']], [u'06', u'07', u'06', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07', u'07'])
    
    def test_writable(self):
        if getattr(settings, 'HAYSTACK_WHOOSH_STORAGE', 'file') == 'file':
            if not os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
                os.makedirs(settings.HAYSTACK_WHOOSH_PATH)
            
            os.chmod(settings.HAYSTACK_WHOOSH_PATH, 0400)
            
            try:
                self.sb.setup()
                self.fail()
            except IOError:
                # Yay. We failed
                pass
            
            os.chmod(settings.HAYSTACK_WHOOSH_PATH, 0755)
    
    def test_slicing(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        page_1 = self.sb.search(u'*', start_offset=0, end_offset=20)
        page_2 = self.sb.search(u'*', start_offset=20, end_offset=30)
        self.assertEqual(len(page_1['results']), 20)
        self.assertEqual([result.pk for result in page_1['results']], [u'%s' % i for i in xrange(1, 21)])
        self.assertEqual(len(page_2['results']), 3)
        self.assertEqual([result.pk for result in page_2['results']], [u'21', u'22', u'23'])
        
        # This used to throw an error.
        page_0 = self.sb.search(u'*', start_offset=0, end_offset=0)
        self.assertEqual(len(page_0['results']), 1)
    
    def test_scoring(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        page_1 = self.sb.search(u'index', start_offset=0, end_offset=20)
        page_2 = self.sb.search(u'index', start_offset=20, end_offset=30)
        self.assertEqual(len(page_1['results']), 20)
        self.assertEqual(["%0.2f" % result.score for result in page_1['results']], ['0.51', '0.51', '0.51', '0.51', '0.51', '0.51', '0.51', '0.51', '0.51', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40', '0.40'])
        self.assertEqual(len(page_2['results']), 3)
        self.assertEqual(["%0.2f" % result.score for result in page_2['results']], ['0.40', '0.40', '0.40'])


class LiveWhooshSearchQueryTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshSearchQueryTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.sb.delete_index()
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = date(2009, 2, 25) - timedelta(days=i)
            self.sample_objs.append(mock)
        
        self.sq = SearchQuery(backend=self.sb)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        super(LiveWhooshSearchQueryTestCase, self).tearDown()
    
    def test_get_spelling(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.sq.add_filter(SQ(content='Indx'))
        self.assertEqual(self.sq.get_spelling_suggestion(), u'index')
    
    def test_log_query(self):
        from django.conf import settings
        from haystack import backends
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        
        # Stow.
        old_debug = settings.DEBUG
        settings.DEBUG = False
        
        len(self.sq.get_results())
        self.assertEqual(len(backends.queries), 0)
        
        settings.DEBUG = True
        # Redefine it to clear out the cached results.
        self.sq = SearchQuery(backend=self.sb)
        self.sq.add_filter(SQ(name='bar'))
        len(self.sq.get_results())
        self.assertEqual(len(backends.queries), 1)
        self.assertEqual(backends.queries[0]['query_string'], 'name:bar')
        
        # And again, for good measure.
        self.sq = SearchQuery(backend=self.sb)
        self.sq.add_filter(SQ(name='baz'))
        self.sq.add_filter(SQ(text='foo'))
        len(self.sq.get_results())
        self.assertEqual(len(backends.queries), 2)
        self.assertEqual(backends.queries[0]['query_string'], 'name:bar')
        self.assertEqual(backends.queries[1]['query_string'], u'(name:baz AND text:foo)')
        
        # Restore.
        settings.DEBUG = old_debug


class LiveWhooshSearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshSearchQuerySetTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        # Stow.
        import haystack
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.sb.delete_index()
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = date(2009, 2, 25) - timedelta(days=i)
            self.sample_objs.append(mock)
        
        self.sq = SearchQuery(backend=self.sb)
        self.sqs = SearchQuerySet(site=self.site)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        
        super(LiveWhooshSearchQuerySetTestCase, self).tearDown()
    
    def test_various_searchquerysets(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        sqs = self.sqs.filter(content='Index')
        self.assertEqual(sqs.query.build_query(), u'Index')
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!')
        self.assertEqual(sqs.query.build_query(), u"'Indexed!'")
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 8, 31))
        self.assertEqual(sqs.query.build_query(), u"('Indexed!' AND pub_date:[to 20090831000000])")
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 2, 23))
        self.assertEqual(sqs.query.build_query(), u"('Indexed!' AND pub_date:[to 20090223000000])")
        self.assertEqual(len(sqs), 2)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 2, 25)).filter(django_id__in=[1, 2]).exclude(name='daniel1')
        self.assertEqual(sqs.query.build_query(), u"('Indexed!' AND pub_date:[to 20090225000000] AND (django_id:\"1\" OR django_id:\"2\") AND NOT (name:daniel1))")
        self.assertEqual(len(sqs), 1)
        
        sqs = self.sqs.auto_query('re-inker')
        self.assertEqual(sqs.query.build_query(), u"'re-inker'")
        self.assertEqual(len(sqs), 0)
        
        sqs = self.sqs.auto_query('0.7 wire')
        self.assertEqual(sqs.query.build_query(), u"('0.7' AND wire)")
        self.assertEqual(len(sqs), 0)
        
        sqs = self.sqs.auto_query("daler-rowney pearlescent 'bell bronze'")
        self.assertEqual(sqs.query.build_query(), u"('daler-rowney' AND pearlescent AND 'bell AND bronze')")
        self.assertEqual(len(sqs), 0)
        
        sqs = self.sqs.models(MockModel)
        self.assertEqual(sqs.query.build_query(), u'django_ct:core.mockmodel')
        self.assertEqual(len(sqs), 3)
    
    def test_all_regression(self):
        sqs = SearchQuerySet()
        self.assertEqual([result.pk for result in sqs], [])
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        sqs = SearchQuerySet()
        self.assertEqual(len(sqs), 3)
        self.assertEqual(sorted([result.pk for result in sqs]), [u'1', u'2', u'3'])
        
        try:
            sqs = repr(SearchQuerySet())
        except:
            self.fail()
    
    def test_regression_space_query(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        sqs = SearchQuerySet().auto_query(" ")
        self.assertEqual(len(sqs), 3)
        sqs = SearchQuerySet().filter(content=" ")
        self.assertEqual(len(sqs), 0)
    
    def test_iter(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        sqs = self.sqs.auto_query('Indexed!')
        results = [int(result.pk) for result in sqs]
        self.assertEqual(sorted(results), [1, 2, 3])
        self.assertEqual(len(backends.queries), 1)
    
    def test_slice(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.auto_query('Indexed!')
        self.assertEqual(sorted([int(result.pk) for result in results[1:3]]), [1, 2])
        self.assertEqual(len(backends.queries), 1)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.auto_query('Indexed!')
        self.assertEqual(int(results[0].pk), 1)
        self.assertEqual(len(backends.queries), 1)
    
    def test_manual_iter(self):
        self.sb.update(self.smmi, self.sample_objs)
        results = self.sqs.auto_query('Indexed!')
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(sorted(results), [1, 2, 3])
        self.assertEqual(len(backends.queries), 1)
    
    def test_fill_cache(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.auto_query('Indexed!')
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(backends.queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 3)
        self.assertEqual(len(backends.queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 3)
        self.assertEqual(len(backends.queries), 2)
    
    def test_cache_is_full(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(self.sqs._cache_is_full(), False)
        results = self.sqs.auto_query('Indexed!')
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(backends.queries), 1)
    
    def test_count(self):
        more_samples = []
        
        for i in xrange(1, 50):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = date(2009, 2, 25) - timedelta(days=i)
            more_samples.append(mock)
        
        self.sb.update(self.smmi, more_samples)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.all()
        self.assertEqual(len(results), 49)
        self.assertEqual(results._cache_is_full(), False)
        self.assertEqual(len(backends.queries), 1)
    
    def test_result_class(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Assert that we're defaulting to ``SearchResult``.
        sqs = self.sqs.all()
        self.assertTrue(isinstance(sqs[0], SearchResult))
        
        # Custom class.
        sqs = self.sqs.result_class(MockSearchResult).all()
        self.assertTrue(isinstance(sqs[0], MockSearchResult))
        
        # Reset to default.
        sqs = self.sqs.result_class(None).all()
        self.assertTrue(isinstance(sqs[0], SearchResult))


class LiveWhooshAutocompleteTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveWhooshAutocompleteTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.wacsi = WhooshAutocompleteMockModelSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshAutocompleteMockModelSearchIndex)
        
        # Stow.
        import haystack
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.sqs = SearchQuerySet(site=self.site)
        
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        for mock in MockModel.objects.all():
            self.wacsi.update_object(mock)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        
        super(LiveWhooshAutocompleteTestCase, self).tearDown()
    
    def test_autocomplete(self):
        autocomplete = self.sqs.autocomplete(text_auto='mod')
        self.assertEqual(autocomplete.count(), 5)
        self.assertEqual([result.pk for result in autocomplete], [u'1', u'12', u'7', u'6', u'14'])
        self.assertTrue('mod' in autocomplete[0].text.lower())
        self.assertTrue('mod' in autocomplete[1].text.lower())
        self.assertTrue('mod' in autocomplete[2].text.lower())
        self.assertTrue('mod' in autocomplete[3].text.lower())
        self.assertTrue('mod' in autocomplete[4].text.lower())
        self.assertEqual(len([result.pk for result in autocomplete]), 5)


class WhooshRoundTripSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, default='')
    name = indexes.CharField()
    is_active = indexes.BooleanField()
    post_count = indexes.IntegerField()
    average_rating = indexes.FloatField()
    pub_date = indexes.DateField()
    created = indexes.DateTimeField()
    tags = indexes.MultiValueField()
    sites = indexes.MultiValueField()
    # For a regression involving lists with nothing in them.
    empty_list = indexes.MultiValueField()
    
    def prepare(self, obj):
        prepped = super(WhooshRoundTripSearchIndex, self).prepare(obj)
        prepped.update({
            'text': 'This is some example text.',
            'name': 'Mister Pants',
            'is_active': True,
            'post_count': 25,
            'average_rating': 3.6,
            'pub_date': date(2009, 11, 21),
            'created': datetime(2009, 11, 21, 21, 31, 00),
            'tags': ['staff', 'outdoor', 'activist', 'scientist'],
            'sites': [3, 5, 1],
            'empty_list': [],
        })
        return prepped


class LiveWhooshRoundTripTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshRoundTripTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.wrtsi = WhooshRoundTripSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshRoundTripSearchIndex)
        
        # Stow.
        import haystack
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.sb.delete_index()
        
        self.sqs = SearchQuerySet(site=self.site)
        
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        # Fake indexing.
        mock = MockModel()
        mock.id = 1
        self.sb.update(self.wrtsi, [mock])
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            shutil.rmtree(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        
        super(LiveWhooshRoundTripTestCase, self).tearDown()
    
    def test_round_trip(self):
        results = self.sqs.filter(id='core.mockmodel.1')
        
        # Sanity check.
        self.assertEqual(results.count(), 1)
        
        # Check the individual fields.
        result = results[0]
        self.assertEqual(result.id, 'core.mockmodel.1')
        self.assertEqual(result.text, 'This is some example text.')
        self.assertEqual(result.name, 'Mister Pants')
        self.assertEqual(result.is_active, True)
        self.assertEqual(result.post_count, 25)
        self.assertEqual(result.average_rating, 3.6)
        self.assertEqual(result.pub_date, datetime(2009, 11, 21, 0, 0))
        self.assertEqual(result.created, datetime(2009, 11, 21, 21, 31, 00))
        self.assertEqual(result.tags, ['staff', 'outdoor', 'activist', 'scientist'])
        self.assertEqual(result.sites, [u'3', u'5', u'1'])
        self.assertEqual(result.empty_list, [])
        
        # Check boolean filtering...
        results = self.sqs.filter(id='core.mockmodel.1', is_active=True)
        self.assertEqual(results.count(), 1)


class LiveWhooshRamStorageTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshRamStorageTestCase, self).setUp()
        
        # Stow.
        self.old_whoosh_storage = getattr(settings, 'HAYSTACK_WHOOSH_STORAGE', 'file')
        settings.HAYSTACK_WHOOSH_STORAGE = 'ram'
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.wrtsi = WhooshRoundTripSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshRoundTripSearchIndex)
        
        # Stow.
        import haystack
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        
        self.sqs = SearchQuerySet(site=self.site)
        
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        # Fake indexing.
        mock = MockModel()
        mock.id = 1
        self.sb.update(self.wrtsi, [mock])
    
    def tearDown(self):
        self.sqs.query.backend.clear()
        
        settings.HAYSTACK_WHOOSH_STORAGE = self.old_whoosh_storage
        
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        
        super(LiveWhooshRamStorageTestCase, self).tearDown()
    
    def test_ram_storage(self):
        results = self.sqs.filter(id='core.mockmodel.1')
        
        # Sanity check.
        self.assertEqual(results.count(), 1)
        
        # Check the individual fields.
        result = results[0]
        self.assertEqual(result.id, 'core.mockmodel.1')
        self.assertEqual(result.text, 'This is some example text.')
        self.assertEqual(result.name, 'Mister Pants')
        self.assertEqual(result.is_active, True)
        self.assertEqual(result.post_count, 25)
        self.assertEqual(result.average_rating, 3.6)
        self.assertEqual(result.pub_date, datetime(2009, 11, 21, 0, 0))
        self.assertEqual(result.created, datetime(2009, 11, 21, 21, 31, 00))
        self.assertEqual(result.tags, ['staff', 'outdoor', 'activist', 'scientist'])
        self.assertEqual(result.sites, [u'3', u'5', u'1'])
        self.assertEqual(result.empty_list, [])
