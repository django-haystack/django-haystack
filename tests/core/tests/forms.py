from django.test import TestCase
from haystack.forms import ModelSearchForm
from haystack import sites
from haystack.query import SearchQuerySet
from haystack.backends.dummy_backend import SearchBackend as DummySearchBackend
from haystack.backends.dummy_backend import SearchQuery as DummySearchQuery
from core.models import MockModel, AnotherMockModel


class ModelSearchFormTestCase(TestCase):
    def setUp(self):
        super(ModelSearchFormTestCase, self).setUp()
        mock_index_site = sites.SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = sites.site
        sites.site = mock_index_site
        
        self.sqs = SearchQuerySet(query=DummySearchQuery(backend=DummySearchBackend()), site=mock_index_site)
    
    def tearDown(self):
        sites.site = self.old_site
        super(ModelSearchFormTestCase, self).tearDown()
    
    def test_models_regression_1(self):
        # Regression for issue #1.
        msf = ModelSearchForm({
            'query': 'test',
            'models': ['core.mockmodel', 'core.anothermockmodel'],
        }, searchqueryset=self.sqs)
        
        self.assertEqual(msf.fields['models'].choices, [('core.anothermockmodel', u'another mock models'), ('core.mockmodel', u'mock models')])
        self.assertEqual(msf.errors, {})
        self.assertEqual(msf.is_valid(), True)
        
        sqs_with_models = msf.search()
        self.assertEqual(len(sqs_with_models.query.models), 2)
