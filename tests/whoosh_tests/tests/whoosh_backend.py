from datetime import timedelta
import os
import shutil
from whoosh.fields import TEXT, ID, KEYWORD, STORED
from whoosh.qparser import QueryParser
from django.conf import settings
from django.utils.datetime_safe import datetime, date
from django.test import TestCase
from haystack import indexes
from haystack.backends.whoosh_backend import SearchBackend, SearchQuery
from haystack.query import SearchQuerySet
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
        
        # Stow.
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
        return searcher.search(self.parser.parse(query))
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Whoosh thinks is there.
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        self.assertEqual([dict(doc) for doc in self.whoosh_search(u'*')], [{'django_id': u'3', 'django_ct': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22T00:00:00', 'id': u'core.mockmodel.3'}, {'django_id': u'2', 'django_ct': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23T00:00:00', 'id': u'core.mockmodel.2'}, {'django_id': u'1', 'django_ct': u'core.mockmodel', 'name': u'daniel1', 'text': u'Indexed!\n1', 'pub_date': u'2009-02-24T00:00:00', 'id': u'core.mockmodel.1'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(len(self.whoosh_search(u'*')), 2)
        self.assertEqual([dict(doc) for doc in self.whoosh_search(u'*')], [{'django_id': u'3', 'django_ct': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22T00:00:00', 'id': u'core.mockmodel.3'}, {'django_id': u'2', 'django_ct': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23T00:00:00', 'id': u'core.mockmodel.2'}])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        self.sb.clear()
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        self.sb.clear([MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        # No query string should always yield zero results.
        self.assertEqual(self.sb.search(u''), {'hits': 0, 'results': []})
        
        # A one letter query string gets nabbed by a stopwords filter. Should
        # always yield zero results.
        self.assertEqual(self.sb.search(u'a'), {'hits': 0, 'results': []})
        
        # Possible AttributeError?
        self.assertEqual(self.sb.search(u'a b'), {'hits': 0, 'results': [], 'spelling_suggestion': '', 'facets': {}})
        
        self.assertEqual(self.sb.search(u'*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search(u'*')['results']], [u'3', u'2', u'1'])
        
        self.assertEqual(self.sb.search(u'', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search(u'index*', highlight=True)['hits'], 3)
        # DRL_FIXME: Uncomment once highlighting works.
        # self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index*', highlight=True)['results']], ['<em>Indexed</em>!\n3', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n1'])
        
        self.assertEqual(self.sb.search(u'Indx')['hits'], 0)
        self.assertEqual(self.sb.search(u'Indx')['spelling_suggestion'], u'index')
        
        self.assertEqual(self.sb.search(u'', facets=['name']), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', facets=['name'])
        results = self.sb.search(u'index*', facets=['name'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search(u'', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}}), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}})
        results = self.sb.search(u'index*', date_facets={'pub_date': {'start_date': date(2008, 2, 26), 'end_date': date(2008, 2, 26), 'gap': '/MONTH'}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search(u'', query_facets={'name': '[* TO e]'}), {'hits': 0, 'results': []})
        results = self.sb.search(u'Index*', query_facets={'name': '[* TO e]'})
        results = self.sb.search(u'index*', query_facets={'name': '[* TO e]'})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        # self.assertEqual(self.sb.search('', narrow_queries=['name:daniel1']), {'hits': 0, 'results': []})
        # results = self.sb.search('Index*', narrow_queries=['name:daniel1'])
        # self.assertEqual(results['hits'], 1)
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search(u'*')), 3)
        
        # Unsupported by Whoosh. Should see empty results.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
    
    def test_delete_index(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        self.sb.delete_index()
        self.assertEqual(self.sb.index.doc_count(), 0)
    
    def test_order_by(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        results = self.sb.search(u'*', sort_by=['pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'3', u'2', u'1'])
        
        results = self.sb.search(u'*', sort_by=['-pub_date'])
        self.assertEqual([result.pk for result in results['results']], [u'1', u'2', u'3'])
        
        results = self.sb.search(u'*', sort_by=['id'])
        self.assertEqual([result.pk for result in results['results']], [u'1', u'2', u'3'])
        
        results = self.sb.search(u'*', sort_by=['-id'])
        self.assertEqual([result.pk for result in results['results']], [u'3', u'2', u'1'])
    
    def test__from_python(self):
        self.assertEqual(self.sb._from_python('abc'), u'abc')
        self.assertEqual(self.sb._from_python(1), u'1')
        self.assertEqual(self.sb._from_python(2653), u'2653')
        self.assertEqual(self.sb._from_python(25.5), u'25.5')
        self.assertEqual(self.sb._from_python([1, 2, 3]), u'[1, 2, 3]')
        self.assertEqual(self.sb._from_python((1, 2, 3)), u'(1, 2, 3)')
        self.assertEqual(self.sb._from_python({'a': 1, 'c': 3, 'b': 2}), u"{'a': 1, 'c': 3, 'b': 2}")
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 9, 16, 14)), u'2009-05-09T16:14:00')
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 9, 0, 0)), u'2009-05-09T00:00:00')
        self.assertEqual(self.sb._from_python(datetime(1899, 5, 18, 0, 0)), u'1899-05-18T00:00:00')
        self.assertEqual(self.sb._from_python(datetime(2009, 5, 18, 1, 16, 30, 250)), u'2009-05-18T01:16:30') # Sorry, we shed the microseconds.
    
    def test__to_python(self):
        self.assertEqual(self.sb._to_python('abc'), 'abc')
        self.assertEqual(self.sb._to_python('1'), 1)
        self.assertEqual(self.sb._to_python('2653'), 2653)
        self.assertEqual(self.sb._to_python('25.5'), 25.5)
        self.assertEqual(self.sb._to_python('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(self.sb._to_python('(1, 2, 3)'), (1, 2, 3))
        self.assertEqual(self.sb._to_python('{"a": 1, "b": 2, "c": 3}'), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(self.sb._to_python('2009-05-09T16:14:00'), datetime(2009, 5, 9, 16, 14))
        self.assertEqual(self.sb._to_python('2009-05-09T00:00:00'), datetime(2009, 5, 9, 0, 0))
        self.assertEqual(self.sb._to_python(None), None)
    
    def test_range_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u'[d TO]')), 3)
        self.assertEqual(len(self.whoosh_search(u'name:[d TO]')), 3)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND name:[d TO]')), 3)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND name:[TO c]')), 0)
    
    def test_date_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u"pub_date:2009\-02\-24T00\:00\:00")), 1)
        self.assertEqual(len(self.whoosh_search(u"pub_date:2009\-08\-30T00\:00\:00")), 0)
        self.assertEqual(len(self.whoosh_search(u'Ind* AND pub_date:[TO 2009\-02\-24T00\:00\:00]')), 3)
    
    def test_escaped_characters_queries(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        self.assertEqual(len(self.whoosh_search(u"Indexed\!")), 3)
        self.assertEqual(len(self.whoosh_search(u"http\:\/\/www\.example\.com")), 0)
    
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
        
        self.assertEqual(self.sb.search(u'*')['hits'], 3)
        self.assertEqual([result.month for result in self.sb.search(u'*')['results']], [u'02', u'02', u'02'])
    
    def test_writable(self):
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
        
        self.sq.add_filter('content', 'Indx')
        self.assertEqual(self.sq.get_spelling_suggestion(), u'index')


class LiveWhooshSearchQuerySetTestCase(TestCase):
    def setUp(self):
        super(LiveWhooshSearchQuerySetTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = WhooshSearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        # Stow.
        import haystack
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
        
        super(LiveWhooshSearchQuerySetTestCase, self).tearDown()
    
    def test_various_searchquerysets(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        sqs = self.sqs.filter(content='Index')
        self.assertEqual(sqs.query.build_query(), u'Index')
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!')
        self.assertEqual(sqs.query.build_query(), u'Indexed\\!')
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 8, 31))
        self.assertEqual(sqs.query.build_query(), u'Indexed\\! AND pub_date:[TO 2009\-08\-31T00\:00\:00]')
        self.assertEqual(len(sqs), 3)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 2, 23))
        self.assertEqual(sqs.query.build_query(), u'Indexed\\! AND pub_date:[TO 2009\\-02\\-23T00\\:00\\:00]')
        self.assertEqual(len(sqs), 2)
        
        sqs = self.sqs.auto_query('Indexed!').filter(pub_date__lte=date(2009, 2, 25)).filter(django_id__in=[1, 2]).exclude(name='daniel1')
        self.assertEqual(sqs.query.build_query(), u'Indexed\\! AND pub_date:[TO 2009\\-02\\-25T00\\:00\\:00] AND (django_id:"1" OR django_id:"2") NOT name:daniel1')
        self.assertEqual(len(sqs), 1)
        
        sqs = self.sqs.auto_query('re-inker')
        self.assertEqual(sqs.query.build_query(), u're\\-inker')
        self.assertEqual(len(sqs), 0)
        
        sqs = self.sqs.auto_query('0.7 wire')
        self.assertEqual(sqs.query.build_query(), u'0\\.7 AND wire')
        self.assertEqual(len(sqs), 0)
        
        sqs = self.sqs.auto_query("daler-rowney pearlescent 'bell bronze'")
        self.assertEqual(sqs.query.build_query(), u'"bell bronze" AND daler\\-rowney AND pearlescent')
        self.assertEqual(len(sqs), 0)
    
    def test_all_regression(self):
        sqs = SearchQuerySet()
        self.assertEqual([result.pk for result in sqs], [])
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        sqs = SearchQuerySet()
        self.assertEqual(len(sqs), 3)
