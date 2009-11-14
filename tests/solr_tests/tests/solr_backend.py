import datetime
import pysolr
from django.conf import settings
from django.test import TestCase
from haystack import backends
from haystack import indexes
from haystack.backends.solr_backend import SearchBackend, SearchQuery
from haystack.exceptions import HaystackError
from haystack.query import SearchQuerySet, RelatedSearchQuerySet, SQ
from haystack.sites import SearchSite
from core.models import MockModel, AnotherMockModel
try:
    set
except NameError:
    from sets import Set as set


class SolrMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')


class SolrMaintainTypeMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    month = indexes.CharField(indexed=False)
    pub_date = indexes.DateField(model_attr='pub_date')
    
    def prepare_month(self, obj):
        return "%02d" % obj.pub_date.month


class SolrSearchBackendTestCase(TestCase):
    def setUp(self):
        super(SolrSearchBackendTestCase, self).setUp()
        
        self.raw_solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL)
        self.raw_solr.delete(q='*:*')
        
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
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'django_id': '1', 'django_ct': 'core.mockmodel', 'name': 'daniel1', 'text': 'Indexed!\n1', 'pub_date': '2009-02-24T00:00:00Z', 'id': 'core.mockmodel.1'}, {'django_id': '2', 'django_ct': 'core.mockmodel', 'name': 'daniel2', 'text': 'Indexed!\n2', 'pub_date': '2009-02-23T00:00:00Z', 'id': 'core.mockmodel.2'}, {'django_id': '3', 'django_ct': 'core.mockmodel', 'name': 'daniel3', 'text': 'Indexed!\n3', 'pub_date': '2009-02-22T00:00:00Z', 'id': 'core.mockmodel.3'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(self.raw_solr.search('*:*').hits, 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(self.raw_solr.search('*:*').hits, 2)
        self.assertEqual(self.raw_solr.search('*:*').docs, [{'django_id': '2', 'django_ct': 'core.mockmodel', 'name': 'daniel2', 'text': 'Indexed!\n2', 'pub_date': '2009-02-23T00:00:00Z', 'id': 'core.mockmodel.2'}, {'django_id': '3', 'django_ct': 'core.mockmodel', 'name': 'daniel3', 'text': 'Indexed!\n3', 'pub_date': '2009-02-22T00:00:00Z', 'id': 'core.mockmodel.3'}])
    
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
        
        self.assertEqual(self.sb.search('', query_facets={'name': '[* TO e]'}), {'hits': 0, 'results': []})
        results = self.sb.search('Index', query_facets={'name': '[* TO e]'})
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
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields, [{'indexed': 'true', 'type': 'text', 'field_name': 'text', 'multi_valued': 'false'}, {'indexed': 'true', 'type': 'date', 'field_name': 'pub_date', 'multi_valued': 'false'}, {'indexed': 'true', 'type': 'text', 'field_name': 'name', 'multi_valued': 'false'}])
    
    def test_verify_type(self):
        import haystack
        haystack.site.unregister(MockModel)
        haystack.site.register(MockModel, SolrMaintainTypeMockSearchIndex)
        self.sb.update(self.smtmmi, self.sample_objs)
        
        self.assertEqual(self.sb.search('*:*')['hits'], 3)
        self.assertEqual([result.month for result in self.sb.search('*:*')['results']], [u'02', u'02', u'02'])


class LiveSolrSearchQueryTestCase(TestCase):
    fixtures = ['initial_data.json']
    
    def setUp(self):
        super(LiveSolrSearchQueryTestCase, self).setUp()
        
        self.sq = SearchQuery(backend=SearchBackend())
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
    
    def test_get_spelling(self):
        self.sq.add_filter(SQ(content='Indx'))
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
        test_site.register(MockModel)
        haystack.site = test_site
        
        self.sqs = SearchQuerySet()
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
    
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
    
    def test_load_all_queryset(self):
        sqs = self.sqs.load_all()
        self.assertRaises(HaystackError, sqs.load_all_queryset, MockModel, MockModel.objects.filter(id__gt=1))
    
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


class SolrMockModelSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')


class SolrAnotherMockModelSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')
    
    def prepare_text(self, obj):
        return u"You might be searching for the user %s" % obj.author


class LiveSolrRegressionsTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveSolrRegressionsTestCase, self).setUp()
        self.sqs = SearchQuerySet()
        
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrMockModelSearchIndex)
        haystack.site = test_site
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
    
    def tearDown(self):
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        # Restore.
        import haystack
        haystack.site = self.old_site
        super(LiveSolrRegressionsTestCase, self).tearDown()
    
    def test_regression_proper_start_offsets(self):
        sqs = self.sqs.filter(text='search')
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


class LiveSolrMoreLikeThisTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveSolrMoreLikeThisTestCase, self).setUp()
        self.sqs = SearchQuerySet()
        
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel, SolrMockModelSearchIndex)
        test_site.register(AnotherMockModel, SolrAnotherMockModelSearchIndex)
        haystack.site = test_site
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
        
        # Force indexing of the content.
        for mock in AnotherMockModel.objects.all():
            mock.save()
        
        self.sqs = SearchQuerySet()
    
    def tearDown(self):
        # Wipe it clean.
        self.sqs.query.backend.clear()
        
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


class LiveSolrRelatedSearchQuerySetTestCase(TestCase):
    """Used to test actual implementation details of the RelatedSearchQuerySet."""
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(LiveSolrRelatedSearchQuerySetTestCase, self).setUp()
        
        # With the models registered, you get the proper bits.
        import haystack
        from haystack.sites import SearchSite
        
        # Stow.
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_site = haystack.site
        test_site = SearchSite()
        test_site.register(MockModel)
        haystack.site = test_site
        
        self.rsqs = RelatedSearchQuerySet()
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
    
    def tearDown(self):
        # Restore.
        import haystack
        haystack.site = self.old_site
        settings.DEBUG = self.old_debug
        super(LiveSolrRelatedSearchQuerySetTestCase, self).tearDown()
    
    def test_load_all(self):
        sqs = self.rsqs.load_all()
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assert_(len(sqs) > 0)
        self.assertEqual(sqs[0].object.foo, u"Registering indexes in Haystack is very similar to registering models and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to override the default indexing behavior for your model you can specify your own ``SearchIndex`` class.  This is useful for ensuring that future-dated or non-live content is not indexed and searchable. Our ``Note`` model has a ``pub_date`` field, so let's update our code to include our own ``SearchIndex`` to exclude indexing future-dated notes:")
    
    def test_load_all_queryset(self):
        sqs = self.rsqs.load_all()
        self.assertEqual(len(sqs._load_all_querysets), 0)
        
        sqs = sqs.load_all_queryset(MockModel, MockModel.objects.filter(id__gt=1))
        self.assert_(isinstance(sqs, SearchQuerySet))
        self.assertEqual(len(sqs._load_all_querysets), 1)
        self.assertEqual([obj.object.id for obj in sqs], range(2, 24))
    
    def test_iter(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        sqs = self.rsqs.all()
        results = [int(result.pk) for result in sqs]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 4)
    
    def test_slice(self):
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
    
    def test_manual_iter(self):
        results = self.rsqs.all()
        
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        results = [int(result.pk) for result in results._manual_iter()]
        self.assertEqual(results, range(1, 24))
        self.assertEqual(len(backends.queries), 4)
    
    def test_fill_cache(self):
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
    
    def test_cache_is_full(self):
        backends.reset_search_queries()
        self.assertEqual(len(backends.queries), 0)
        self.assertEqual(self.rsqs._cache_is_full(), False)
        results = self.rsqs.all()
        fire_the_iterator_and_fill_cache = [result for result in results]
        self.assertEqual(results._cache_is_full(), True)
        self.assertEqual(len(backends.queries), 5)
