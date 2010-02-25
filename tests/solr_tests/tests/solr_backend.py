import datetime
import logging
import pysolr
from django.conf import settings
from django.test import TestCase
from haystack import backends
from haystack.indexes import *
from haystack.backends.solr_backend import SearchBackend, SearchQuery
from haystack.exceptions import HaystackError
from haystack.query import SearchQuerySet, RelatedSearchQuerySet, SQ
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel
try:
    set
except NameError:
    from sets import Set as set


def clear_solr_index():
    # Wipe it clean.
    print 'Clearing out Solr...'
    raw_solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL)
    raw_solr.delete(q='*:*')


class SolrMockSearchIndex(RealTimeSearchIndex):
    text = CharField(document=True, use_template=True)
    name = CharField(model_attr='author', faceted=True)
    pub_date = DateField(model_attr='pub_date')


class SolrMaintainTypeMockSearchIndex(RealTimeSearchIndex):
    text = CharField(document=True, use_template=True)
    month = CharField(indexed=False)
    pub_date = DateField(model_attr='pub_date')
    
    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month


class SolrMockModelSearchIndex(RealTimeSearchIndex):
    text = CharField(model_attr='foo', document=True)
    name = CharField(model_attr='author')
    pub_date = DateField(model_attr='pub_date')


class SolrAnotherMockModelSearchIndex(RealTimeSearchIndex):
    text = CharField(document=True)
    name = CharField(model_attr='author')
    pub_date = DateField(model_attr='pub_date')
    
    def prepare_text(self, obj):
        return u"You might be searching for the user %s" % obj.author


class SolrRoundTripSearchIndex(RealTimeSearchIndex):
    text = CharField(document=True, default='')
    name = CharField()
    is_active = BooleanField()
    post_count = IntegerField()
    average_rating = FloatField()
    pub_date = DateField()
    created = DateTimeField()
    tags = MultiValueField()
    sites = MultiValueField()
    
    def prepare(self, obj):
        prepped = super(SolrRoundTripSearchIndex, self).prepare(obj)
        prepped.update({
            'text': 'This is some example text.',
            'name': 'Mister Pants',
            'is_active': True,
            'post_count': 25,
            'average_rating': 3.6,
            'pub_date': datetime.date(2009, 11, 21),
            'created': datetime.datetime(2009, 11, 21, 21, 31, 00),
            'tags': ['staff', 'outdoor', 'activist', 'scientist'],
            'sites': [3, 5, 1],
        })
        return prepped


class SolrSearchBackendTestCase(TestCase):
    def setUp(self):
        super(SolrSearchBackendTestCase, self).setUp()
        
        # Wipe it clean.
        self.raw_solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL)
        clear_solr_index()
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = SolrMockSearchIndex(MockModel, backend=self.sb)
        self.smtmmi = SolrMaintainTypeMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, SolrMockSearchIndex)
        
        # Stow.
        import haystack
        self.old_site = haystack.site
        haystack.site = self.site
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)
    
    def tearDown(self):
        import haystack
        haystack.site = self.old_site
        super(SolrSearchBackendTestCase, self).tearDown()
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Solr thinks is there.
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        self.assertEqual(self.raw_solr.search('*:*').docs, [
            {
                'django_id': '1',
                'django_ct': 'core.mockmodel',
                'name': 'daniel1',
                'name_exact': 'daniel1',
                'text': 'Indexed!\n1',
                'pub_date': '2009-02-24T00:00:00Z',
                'id': 'core.mockmodel.1'
            },
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00Z',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00Z',
                'id': 'core.mockmodel.3'
            }
        ])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_solr.search('*:*').hits, 2)
        self.assertEqual(self.raw_solr.search('*:*').docs, [
            {
                'django_id': '2',
                'django_ct': 'core.mockmodel',
                'name': 'daniel2',
                'name_exact': 'daniel2',
                'text': 'Indexed!\n2',
                'pub_date': '2009-02-23T00:00:00Z',
                'id': 'core.mockmodel.2'
            },
            {
                'django_id': '3',
                'django_ct': 'core.mockmodel',
                'name': 'daniel3',
                'name_exact': 'daniel3',
                'text': 'Indexed!\n3',
                'pub_date': '2009-02-22T00:00:00Z',
                'id': 'core.mockmodel.3'
            }
        ])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear()
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.assertEqual(self.raw_solr.search('*:*').hits, 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.assertEqual(self.sb.search(''), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*:*')['results']], ['1', '2', '3'])
        
        self.assertEqual(self.sb.search('', highlight=True), {'hits': 0, 'results': []})
        self.assertEqual(self.sb.search('Index', highlight=True)['hits'], 3)
        self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index', highlight=True)['results']], ['<em>Indexed</em>!\n1', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n3'])
        
        self.assertEqual(self.sb.search('Indx')['hits'], 0)
        self.assertEqual(self.sb.search('Indx')['spelling_suggestion'], 'index')
        self.assertEqual(self.sb.search('Indx', spelling_query='indexy')['spelling_suggestion'], 'index')
        
        self.assertEqual(self.sb.search('', facets=['name']), {'hits': 0, 'results': []})
        results = self.sb.search('Index', facets=['name'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['name'], [('daniel1', 1), ('daniel2', 1), ('daniel3', 1)])
        
        self.assertEqual(self.sb.search('', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 3, 26), 'gap_by': 'month', 'gap_amount': 1}}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 3, 26), 'gap_by': 'month', 'gap_amount': 1}})
        self.assertEqual(results['hits'], 3)
        # DRL_TODO: Correct output but no counts. Another case of needing better test data?
        # self.assertEqual(results['facets']['dates']['pub_date'], {'end': '2008-02-26T00:00:00Z', 'gap': '/MONTH'})
        
        self.assertEqual(self.sb.search('', query_facets=[('name', '[* TO e]')]), {'hits': 0, 'results': []})
        results = self.sb.search('Index', query_facets=[('name', '[* TO e]')])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['queries'], {'name:[* TO e]': 3})
        
        self.assertEqual(self.sb.search('', narrow_queries=set(['name:daniel1'])), {'hits': 0, 'results': []})
        results = self.sb.search('Index', narrow_queries=set(['name:daniel1']))
        self.assertEqual(results['hits'], 1)
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        # A functional MLT example with enough data to work is below. Rely on
        # this to ensure the API is correct enough.
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
        self.assertEqual([result.pk for result in self.sb.more_like_this(self.sample_objs[0])['results']], [])
    
    def test_build_schema(self):
        (content_field_name, fields) = self.sb.build_schema(self.site.all_searchfields())
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(fields), 4)
        self.assertEqual(fields, [
            {
                'indexed': 'true',
                'type': 'text',
                'field_name': 'text',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'date',
                'field_name': 'pub_date',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'text',
                'field_name': 'name',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'string',
                'field_name': 'name_exact',
                'multi_valued': 'false'
            }
        ])
    
    def test_verify_type(self):
        import haystack
        haystack.site.unregister(MockModel)
        haystack.site.register(MockModel, SolrMaintainTypeMockSearchIndex)
        self.sb.update(self.smtmmi, self.sample_objs)
        
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.month for result in self.sb.search('*:*')['results']], [u'02', u'02', u'02'])


class CaptureHandler(logging.Handler):
    logs_seen = []
    
    def emit(self, record):
        CaptureHandler.logs_seen.append(record)


class FailedSolrSearchBackendTestCase(TestCase):
    def test_all_cases(self):
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)
        
        # Stow.
        # Point the backend at a URL that doesn't exist so we can watch the
        # sparks fly.
        old_solr_url = settings.HAYSTACK_SOLR_URL
        settings.HAYSTACK_SOLR_URL = "%s/foo/" % settings.HAYSTACK_SOLR_URL
        cap = CaptureHandler()
        logging.getLogger('haystack').addHandler(cap)
        import haystack
        logging.getLogger('haystack').removeHandler(haystack.stream)
        
        # Setup the rest of the bits.
        site = SearchSite()
        site.register(MockModel, SolrMockSearchIndex)
        sb = SearchBackend(site=site)
        smmi = SolrMockSearchIndex(MockModel, backend=sb)
        
        # Prior to the addition of the try/except bits, these would all fail miserably.
        self.assertEqual(len(CaptureHandler.logs_seen), 0)
        sb.update(smmi, self.sample_objs)
        self.assertEqual(len(CaptureHandler.logs_seen), 1)
        sb.remove(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 2)
        sb.search('search')
        self.assertEqual(len(CaptureHandler.logs_seen), 3)
        sb.more_like_this(self.sample_objs[0])
        self.assertEqual(len(CaptureHandler.logs_seen), 4)
        sb.clear([MockModel])
        self.assertEqual(len(CaptureHandler.logs_seen), 5)
        sb.clear()
        self.assertEqual(len(CaptureHandler.logs_seen), 6)
        
        # Restore.
        settings.HAYSTACK_SOLR_URL = old_solr_url
        logging.getLogger('haystack').removeHandler(cap)
        logging.getLogger('haystack').addHandler(haystack.stream)


class LiveSolrSearchQueryTestCase(TestCase):
    fixtures = ['initial_data.json']
    
    def setUp(self):
        super(LiveSolrSearchQueryTestCase, self).setUp()
        
        # Wipe it clean.
        clear_solr_index()
        
        site = SearchSite()
        site.register(MockModel, SolrMockSearchIndex)
        sb = SearchBackend(site=site)
        smmi = SolrMockSearchIndex(MockModel, backend=sb)
        
        self.sq = SearchQuery(backend=sb)
        
        # Force indexing of the content.
        mockmodel_index = site.get_index(MockModel)
        mockmodel_index.update()
    
    def test_get_spelling(self):
        self.sq.add_filter(SQ(content='Indexy'))
        self.assertEqual(self.sq.get_spelling_suggestion(), u'index')
        self.assertEqual(self.sq.get_spelling_suggestion('indexy'), u'index')
    
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
        self.sq = SearchQuery(backend=SearchBackend())
        self.sq.add_filter(SQ(name='bar'))
        len(self.sq.get_results())
        self.assertEqual(len(backends.queries), 1)
        self.assertEqual(backends.queries[0]['query_string'], 'name:bar')
        
        # And again, for good measure.
        self.sq = SearchQuery(backend=SearchBackend())
        self.sq.add_filter(SQ(name='bar'))
        self.sq.add_filter(SQ(text='moof'))
        len(self.sq.get_results())
        self.assertEqual(len(backends.queries), 2)
        self.assertEqual(backends.queries[0]['query_string'], 'name:bar')
        self.assertEqual(backends.queries[1]['query_string'], u'(name:bar AND text:moof)')
        
        # Restore.
        settings.DEBUG = old_debug


lssqstc_all_loaded = None


class LiveSolrSearchQuerySetTestCase(TestCase):
    """Used to test actual implementation details of the SearchQuerySet."""
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveSolrSearchQuerySetTestCase, self).setUp()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrMockModelSearchIndex)
        haystack.site = test_site
        
        self.sqs = SearchQuerySet()
        self.rsqs = RelatedSearchQuerySet()
        
        # Ugly but not constantly reindexing saves us almost 50% runtime.
        global lssqstc_all_loaded
        
        if lssqstc_all_loaded is None:
            print 'Reloading data...'
            lssqstc_all_loaded = True
            
            # Wipe it clean.
            clear_solr_index()
            
            # Force indexing of the content.
            mockmodel_index = test_site.get_index(MockModel)
            mockmodel_index.update()
    
    def tearDown(self):
        # Restore.
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        super(LiveSolrSearchQuerySetTestCase, self).tearDown()
    
    def test_load_all(self):
        sqs = self.sqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assert_(len(sqs) > 0)
        self.assertEqual(sqs[0].object.foo, u"Registering indexes in Haystack is very similar to registering models and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to override the default indexing behavior for your model you can specify your own ``SearchIndex`` class.  This is useful for ensuring that future-dated or non-live content is not indexed and searchable. Our ``Note`` model has a ``pub_date`` field, so let's update our code to include our own ``SearchIndex`` to exclude indexing future-dated notes:")
    
    def test_iter(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        sqs = self.sqs.all()
        results = [int(result.pk) for result in sqs]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 3)
    
    def test_slice(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(len(backends.queries), 1)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.all()
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(backends.queries), 1)
    
    def test_manual_iter(self):
        results = self.sqs.all()
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 3)
    
    def test_fill_cache(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.sqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(backends.queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(backends.queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(backends.queries), 2)
    
    def test_cache_is_full(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(self.sqs._cache_is_full(), False)
        results = self.sqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(backends.queries), 3)
    
    def test___and__(self):
        sqs1 = self.sqs.filter(content='foo')
        sqs2 = self.sqs.filter(content='bar')
        sqs = sqs1 & sqs2
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'(foo AND bar)')
        
        # Now for something more complex...
        sqs3 = self.sqs.exclude(title='moof').filter(SQ(content='foo') | SQ(content='baz'))
        sqs4 = self.sqs.filter(content='bar')
        sqs = sqs3 & sqs4
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 3)
        self.assertEqual(sqs.query.build_query(), u'(NOT (title:moof) AND (foo OR baz) AND bar)')
    
    def test___or__(self):
        sqs1 = self.sqs.filter(content='foo')
        sqs2 = self.sqs.filter(content='bar')
        sqs = sqs1 | sqs2
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'(foo OR bar)')
        
        # Now for something more complex...
        sqs3 = self.sqs.exclude(title='moof').filter(SQ(content='foo') | SQ(content='baz'))
        sqs4 = self.sqs.filter(content='bar').models(MockModel)
        sqs = sqs3 | sqs4
        
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs.query.query_filter), 2)
        self.assertEqual(sqs.query.build_query(), u'((NOT (title:moof) AND (foo OR baz)) OR bar)')
    
    def test_auto_query(self):
        # Ensure bits in exact matches get escaped properly as well.
        # This will break horrifically if escaping isn't working.
        sqs = self.sqs.auto_query('"pants:rule"')
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(repr(sqs.query.query_filter), '<SQ: AND content__exact=pants\\:rule>')
        self.assertEqual(sqs.query.build_query(), u'pants\\:rule')
        self.assertEqual(len(sqs), 0)
    
    # Regressions
    
    def test_regression_proper_start_offsets(self):
        sqs = self.sqs.filter(text='index')
        self.assertNotEqual(sqs.count(), 0)
        
        id_counts = {}
        
        for item in sqs:
            if item.id in id_counts:
                id_counts[item.id] += 1
            else:
                id_counts[item.id] = 1
        
        for key, value in id_counts.items():
            if value > 1:
                self.fail("Result with id '%s' seen more than once in the results." % key)
    
    def test_regression_raw_search_breaks_slicing(self):
        sqs = self.sqs.raw_search('text: index')
        page_1 = [result.pk for result in sqs[0:10]]
        page_2 = [result.pk for result in sqs[10:20]]
        
        for pk in page_2:
            if pk in page_1:
                self.fail("Result with id '%s' seen more than once in the results." % pk)
    
    # RelatedSearchQuerySet Tests
    
    def test_related_load_all(self):
        sqs = self.rsqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assert_(len(sqs) > 0)
        self.assertEqual(sqs[0].object.foo, u"Registering indexes in Haystack is very similar to registering models and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to override the default indexing behavior for your model you can specify your own ``SearchIndex`` class.  This is useful for ensuring that future-dated or non-live content is not indexed and searchable. Our ``Note`` model has a ``pub_date`` field, so let's update our code to include our own ``SearchIndex`` to exclude indexing future-dated notes:")
    
    def test_related_load_all_queryset(self):
        sqs = self.rsqs.load_all()
        self.assertEqual(len(sqs._load_all_querysets), 0)
        
        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], range(2, 24))
        
        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=10))
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], range(11, 24))
        self.assertEqual([obj.object.id for obj in sqs[10:20]], [21, 22, 23])
    
    def test_related_iter(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        sqs = self.rsqs.all()
        results = [int(result.pk) for result in sqs]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 4)
    
    def test_related_slice(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[1:11]], [2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(len(backends.queries), 3)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.rsqs.all()
        self.assertEqual(int(results[21].pk), 22)
        self.assertEqual(len(backends.queries), 4)
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.rsqs.all()
        self.assertEqual([int(result.pk) for result in results[20:30]], [21, 22, 23])
        self.assertEqual(len(backends.queries), 4)
    
    def test_related_manual_iter(self):
        results = self.rsqs.all()
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 4)
    
    def test_related_fill_cache(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = self.rsqs.all()
        self.assertEqual(len(results._result_cache), 0)
        self.assertEqual(len(backends.queries), 0)
        results._fill_cache(0, 10)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 10)
        self.assertEqual(len(backends.queries), 1)
        results._fill_cache(10, 20)
        self.assertEqual(len([result for result in results._result_cache if result is not None]), 20)
        self.assertEqual(len(backends.queries), 2)
    
    def test_related_cache_is_full(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(self.rsqs._cache_is_full(), False)
        results = self.rsqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(backends.queries), 5)


class LiveSolrMoreLikeThisTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveSolrMoreLikeThisTestCase, self).setUp()
        
        # Wipe it clean.
        clear_solr_index()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrMockModelSearchIndex)
        test_site.register(AnotherMockModel, SolrAnotherMockModelSearchIndex)
        haystack.site = test_site
        
        self.sqs = SearchQuerySet()
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
        
        # Force indexing of the content.
        for mock in AnotherMockModel.objects.all():
            mock.save()
    
    def tearDown(self):
        # Restore.
        import haystack
        haystack.site = self.old_site
        super(LiveSolrMoreLikeThisTestCase, self).tearDown()
    
    def test_more_like_this(self):
        mlt = self.sqs.more_like_this(MockModel.objects.get(pk=1))
        self.assertEqual(mlt.count(), 25)
        self.assertEqual([result.pk for result in mlt], ['6', '14', '4', '10', '22', '5', '3', '12', '2', '23', '18', '19', '13', '7', '15', '21', '9', '1', '2', '20', '16', '17', '8', '11'])
        
        alt_mlt = self.sqs.filter(name='daniel3').more_like_this(MockModel.objects.get(pk=3))
        self.assertEqual(alt_mlt.count(), 11)
        self.assertEqual([result.pk for result in alt_mlt], ['23', '13', '17', '16', '22', '19', '4', '10', '1', '2'])
        
        alt_mlt_with_models = self.sqs.models(MockModel).more_like_this(MockModel.objects.get(pk=1))
        self.assertEqual(alt_mlt_with_models.count(), 23)
        self.assertEqual([result.pk for result in alt_mlt_with_models], ['6', '14', '4', '10', '22', '5', '3', '12', '2', '23', '18', '19', '13', '7', '15', '21', '9', '20', '16', '17', '8', '11'])
        
        if hasattr(MockModel.objects, 'defer'):
            # Make sure MLT works with deferred bits.
            mi = MockModel.objects.defer('foo').get(pk=1)
            self.assertEqual(mi._deferred, True)
            deferred = self.sqs.models(MockModel).more_like_this(mi)
            self.assertEqual(alt_mlt_with_models.count(), 23)
            self.assertEqual([result.pk for result in alt_mlt_with_models], ['6', '14', '4', '10', '22', '5', '3', '12', '2', '23', '18', '19', '13', '7', '15', '21', '9', '20', '16', '17', '8', '11'])


class LiveSolrRoundTripTestCase(TestCase):
    def setUp(self):
        super(LiveSolrRoundTripTestCase, self).setUp()
        
        # Wipe it clean.
        clear_solr_index()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrRoundTripSearchIndex)
        haystack.site = test_site
        
        self.sqs = SearchQuerySet()
        
        # Fake indexing.
        sb = SearchBackend(site=test_site)
        srtsi = SolrRoundTripSearchIndex(MockModel)
        mock = MockModel()
        mock.id = 1
        sb.update(srtsi, [mock])
    
    def tearDown(self):
        # Restore.
        import haystack
        haystack.site = self.old_site
        super(LiveSolrRoundTripTestCase, self).tearDown()
    
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
        self.assertEqual(result.pub_date, datetime.date(2009, 11, 21))
        self.assertEqual(result.created, datetime.datetime(2009, 11, 21, 21, 31, 00))
        self.assertEqual(result.tags, ['staff', 'outdoor', 'activist', 'scientist'])
        self.assertEqual(result.sites, [3, 5, 1])
