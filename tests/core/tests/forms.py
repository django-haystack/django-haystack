from django.test import TestCase
from haystack.forms import SearchForm, ModelSearchForm, model_choices, FacetedSearchForm
import haystack
from haystack.sites import SearchSite
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from haystack.backends.dummy_backend import SearchBackend as DummySearchBackend
from haystack.backends.dummy_backend import SearchQuery as DummySearchQuery
from core.models import MockModel, AnotherMockModel


class SearchFormTestCase(TestCase):
    def setUp(self):
        super(SearchFormTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.sqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()), site=mock_index_site)
    
    def tearDown(self):
        haystack.site = self.old_site
        super(SearchFormTestCase, self).tearDown()
    
    def test_unbound(self):
        sf = SearchForm({}, searchqueryset=self.sqs)
        
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        
        # This shouldn't blow up.
        sqs = sf.search()
        self.assertTrue(isinstance(sqs, EmptySearchQuerySet))


class ModelSearchFormTestCase(TestCase):
    def setUp(self):
        super(ModelSearchFormTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.sqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()), site=mock_index_site)
    
    def tearDown(self):
        haystack.site = self.old_site
        super(ModelSearchFormTestCase, self).tearDown()
    
    def test_models_regression_1(self):
        # Regression for issue #1.
        msf = ModelSearchForm({
            'query': 'test',
            'models': ['core.mockmodel', 'core.anothermockmodel'],
        }, searchqueryset=self.sqs)
        
        self.assertEqual(msf.fields['models'].choices, [('core.anothermockmodel', u'Another mock models'), ('core.mockmodel', u'Mock models')])
        self.assertEqual(msf.errors, {})
        self.assertEqual(msf.is_valid(), True)
        
        sqs_with_models = msf.search()
        self.assertEqual(len(sqs_with_models.query.models), 2)
    
    def test_model_choices(self):
        mis = SearchSite()
        mis.register(MockModel)
        mis.register(AnotherMockModel)
        self.assertEqual(len(model_choices(site=mis)), 2)
        self.assertEqual([option[1] for option in model_choices(site=mis)], [u'Another mock models', u'Mock models'])


class FacetedSearchFormTestCase(TestCase):
    def setUp(self):
        super(FacetedSearchFormTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.sqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()), site=mock_index_site)
    
    def tearDown(self):
        haystack.site = self.old_site
        super(FacetedSearchFormTestCase, self).tearDown()
    
    def test_init_with_selected_facets(self):
        sf = FacetedSearchForm({}, searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, [])
        
        sf = FacetedSearchForm({}, selected_facets=[], searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, [])
        
        sf = FacetedSearchForm({}, selected_facets=['author:daniel'], searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, ['author:daniel'])
        
        sf = FacetedSearchForm({}, selected_facets=['author:daniel', 'author:chris'], searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, ['author:daniel', 'author:chris'])
    
    def test_search(self):
        sf = FacetedSearchForm({'q': 'test'}, selected_facets=[], searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())
        
        # Test the "skip no-colon" bits.
        sf = FacetedSearchForm({'q': 'test'}, selected_facets=['authordaniel'], searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())
        
        sf = FacetedSearchForm({'q': 'test'}, selected_facets=['author:daniel'], searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set([u'author:"daniel"']))
        
        sf = FacetedSearchForm({'q': 'test'}, selected_facets=['author:daniel', 'author:chris'], searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set([u'author:"daniel"', u'author:"chris"']))
