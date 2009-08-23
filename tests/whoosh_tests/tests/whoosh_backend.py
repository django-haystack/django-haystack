import datetime
import os
from whoosh.fields import ID, TEXT, KEYWORD, STORED
from whoosh.qparser import QueryParser
from django.conf import settings
from django.test import TestCase
from haystack import indexes
from haystack.backends.whoosh_backend import SearchBackend, SearchQuery
from haystack import sites
from core.models import MockModel, AnotherMockModel


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


class WhooshMaintainTypeMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateField(model_attr='pub_date')
    
    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month


class WhooshSearchSite(sites.SearchSite):
    pass


class WhooshSearchBackendTestCase(TestCase):
    def setUp(self):
        super(WhooshSearchBackendTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = WhooshSearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.wmtmmi = WhooshMaintainTypeMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.raw_whoosh.delete_by_query(q=self.parser.parse('*'))
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            index_files = os.listdir(settings.HAYSTACK_WHOOSH_PATH)
        
            for index_file in index_files:
                os.remove(os.path.join(settings.HAYSTACK_WHOOSH_PATH, index_file))
        
            os.removedirs(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        
        # Restore.
        import haystack
        haystack.site = self.old_site
        
        super(WhooshSearchBackendTestCase, self).tearDown()
    
    def whoosh_search(self, query):
        searcher = self.raw_whoosh.searcher()
        return searcher.search(self.parser.parse(query))
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Whoosh thinks is there.
        self.assertEqual(len(self.whoosh_search('*')), 3)
        self.assertEqual([dict(doc) for doc in self.whoosh_search('*')], [{'django_id': u'3', 'django_ct': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22T00:00:00', 'id': u'core.mockmodel.3'}, {'django_id': u'2', 'django_ct': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23T00:00:00', 'id': u'core.mockmodel.2'}, {'django_id': u'1', 'django_ct': u'core.mockmodel', 'name': u'daniel1', 'text': u'Indexed!\n1', 'pub_date': u'2009-02-24T00:00:00', 'id': u'core.mockmodel.1'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(len(self.whoosh_search('*')), 2)
        self.assertEqual([dict(doc) for doc in self.whoosh_search('*')], [{'django_id': u'3', 'django_ct': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22T00:00:00', 'id': u'core.mockmodel.3'}, {'django_id': u'2', 'django_ct': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23T00:00:00', 'id': u'core.mockmodel.2'}])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear()
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        # No query string should always yield zero results.
        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        
        # A one letter query string gets nabbed by a stopwords filter. Should
        # always yield zero results.
        self.assertEqual(self.sb.search('a'), {'hits': 0, 'results': []})
        
        # Possible AttributeError?
        self.assertEqual(self.sb.search('a b'), {'hits': 0, 'results': []})
        
        self.assertEqual(self.sb.search('*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*')['results']], [u'3', u'2', u'1'])
        
        self.assertEqual(self.sb.search('', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('Index*', highlight=True)['hits'], 3)
        # DRL_FIXME: Uncomment once highlighting works.
        # self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index*', highlight=True)['results']], ['<em>Indexed</em>!\n3', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n1'])
        
        self.assertEqual(self.sb.search('Indx')['hits'], 0)
        self.assertEqual(self.sb.search('Indx')['spelling_suggestion'], u'index')
        
        self.assertEqual(self.sb.search('', facets=['name']), {'hits': 0, 'results': []})
        results = self.sb.search('Index*', facets=['name'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search('', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 2, 26), 'gap': '/MONTH'}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index*', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 2, 26), 'gap': '/MONTH'}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search('', query_facets={'name': '[* TO e]'}), {'hits': 0, 'results': []})
        results = self.sb.search('Index*', query_facets={'name': '[* TO e]'})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        # self.assertEqual(self.sb.search('', narrow_queries=['name:daniel1']), {'hits': 0, 'results': []})
        # results = self.sb.search('Index*', narrow_queries=['name:daniel1'])
        # self.assertEqual(results['hits'], 1)
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        # Unsupported by Whoosh. Should see empty results.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
    
    def test_delete_index(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        self.sb.delete_index()
        self.assertEqual(self.sb.index.doc_count(), 0)
    
    def test_order_by(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        results = self.sb.search('*', sort_by=['pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'1', u'2', u'3'])
        
        results = self.sb.search('*', sort_by=['-pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'3', u'2', u'1'])
    
    def test__from_python(self):
        self.assertEqual(self.sb._from_python('abc'), u'abc')
        self.assertEqual(self.sb._from_python(1), u'1')
        self.assertEqual(self.sb._from_python(2653), u'2653')
        self.assertEqual(self.sb._from_python(25.5), u'25.5')
        self.assertEqual(self.sb._from_python([1, 2, 3]), u'[1, 2, 3]')
        self.assertEqual(self.sb._from_python((1, 2, 3)), u'(1, 2, 3)')
        self.assertEqual(self.sb._from_python({'a': 1, 'c': 3, 'b': 2}), u"{'a': 1, 'c': 3, 'b': 2}")
        self.assertEqual(self.sb._from_python(datetime.datetime(2009, 5, 9, 16, 14)), u'2009-05-09T16:14:00')
        self.assertEqual(self.sb._from_python(datetime.datetime(2009, 5, 9, 0, 0)), u'2009-05-09T00:00:00')
        self.assertEqual(self.sb._from_python(datetime.datetime(1899, 5, 18, 0, 0)), u'1899-05-18T00:00:00')
        self.assertEqual(self.sb._from_python(datetime.datetime(2009, 5, 18, 1, 16, 30, 250)), u'2009-05-18T01:16:30.000250')
    
    def test__to_python(self):
        self.assertEqual(self.sb._to_python('abc'), 'abc')
        self.assertEqual(self.sb._to_python('1'), 1)
        self.assertEqual(self.sb._to_python('2653'), 2653)
        self.assertEqual(self.sb._to_python('25.5'), 25.5)
        self.assertEqual(self.sb._to_python('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(self.sb._to_python('(1, 2, 3)'), (1, 2, 3))
        self.assertEqual(self.sb._to_python('{"a": 1, "b": 2, "c": 3}'), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(self.sb._to_python('2009-05-09T16:14:00'), datetime.datetime(2009, 5, 9, 16, 14))
        self.assertEqual(self.sb._to_python('2009-05-09T00:00:00'), datetime.datetime(2009, 5, 9, 0, 0))
    
    def test_build_schema(self):
        self.site.unregister(MockModel)
        self.site.register(MockModel, AllTypesWhooshMockSearchIndex)
        
        (content_field_name, schema) = self.sb.build_schema(self.site.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(schema._names), 8)
        self.assertEqual(schema._names, ['django_ct', 'django_id', 'id', 'name', 'pub_date', 'seen_count', 'sites', 'text'])
        self.assert_(isinstance(schema._by_name['text'], TEXT))
        self.assert_(isinstance(schema._by_name['pub_date'], ID))
        self.assert_(isinstance(schema._by_name['seen_count'], STORED))
        self.assert_(isinstance(schema._by_name['sites'], KEYWORD))
    
    def test_verify_type(self):
        import haystack
        haystack.site.unregister(MockModel)
        haystack.site.register(MockModel, WhooshMaintainTypeMockSearchIndex)
        self.sb.setup()
        self.sb.update(self.wmtmmi, self.sample_objs)
        
        self.assertEqual(self.sb.search('*')['hits'], 3)
        self.assertEqual([result.month for result in self.sb.search('*')['results']], [u'02', u'02', u'02'])


class LiveWhooshSearchQueryTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshSearchQueryTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = WhooshSearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.raw_whoosh.delete_by_query(q=self.parser.parse('*'))
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)
        
        self.sq = SearchQuery(backend=self.sb)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            index_files = os.listdir(settings.HAYSTACK_WHOOSH_PATH)
        
            for index_file in index_files:
                os.remove(os.path.join(settings.HAYSTACK_WHOOSH_PATH, index_file))
        
            os.removedirs(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        super(LiveWhooshSearchQueryTestCase, self).tearDown()
    
    def test_get_spelling(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.sq.add_filter('content', 'Indx')
        self.assertEqual(self.sq.get_spelling_suggestion(), u'index')
