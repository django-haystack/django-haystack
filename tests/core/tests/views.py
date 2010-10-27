from threading import Thread
import Queue
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms
from django.http import HttpRequest
from django.test import TestCase
import haystack
from haystack.forms import model_choices, SearchForm, ModelSearchForm
from haystack.query import EmptySearchQuerySet
from haystack.sites import SearchSite
from haystack.views import SearchView, FacetedSearchView, search_view_factory
from core.models import MockModel, AnotherMockModel


class InitialedSearchForm(SearchForm):
    q = forms.CharField(initial='Search for...', required=False, label='Search')


class SearchViewTestCase(TestCase):
    def setUp(self):
        super(SearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(SearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_query(self):
        response = self.client.get(reverse('haystack_search'), {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['page'].object_list[0].content_type(), 'haystack.dummymodel')
        self.assertEqual(response.context[-1]['page'].object_list[0].pk, 1)
    
    def test_invalid_page(self):
        response = self.client.get(reverse('haystack_search'), {'q': 'hello world', 'page': '165233'})
        self.assertEqual(response.status_code, 404)
    
    def test_empty_results(self):
        sv = SearchView()
        sv.request = HttpRequest()
        sv.form = sv.build_form()
        self.assert_(isinstance(sv.get_results(), EmptySearchQuerySet))
    
    def test_initial_data(self):
        sv = SearchView(form_class=InitialedSearchForm)
        sv.request = HttpRequest()
        form = sv.build_form()
        self.assert_(isinstance(form, InitialedSearchForm))
        self.assertEqual(form.fields['q'].initial, 'Search for...')
        self.assertEqual(form.as_p(), u'<p><label for="id_q">Search:</label> <input type="text" name="q" value="Search for..." id="id_q" /></p>')
    
    def test_thread_safety(self):
        exceptions = []
        
        def threaded_view(queue, view, request):
            import time; time.sleep(2)
            try:
                inst = view(request)
                queue.put(request.GET['name'])
            except Exception, e:
                exceptions.append(e)
                raise
        
        class ThreadedSearchView(SearchView):
            def __call__(self, request):
                print "Name: %s" % request.GET['name']
                return super(ThreadedSearchView, self).__call__(request)
        
        view = search_view_factory(view_class=ThreadedSearchView)
        queue = Queue.Queue()
        request_1 = HttpRequest()
        request_1.GET = {'name': 'foo'}
        request_2 = HttpRequest()
        request_2.GET = {'name': 'bar'}
        
        th1 = Thread(target=threaded_view, args=(queue, view, request_1))
        th2 = Thread(target=threaded_view, args=(queue, view, request_2))
        
        th1.start()
        th2.start()
        th1.join()
        th2.join()
        
        foo = queue.get()
        bar = queue.get()
        self.assertNotEqual(foo, bar)


class ResultsPerPageTestCase(TestCase):
    urls = 'core.tests.results_per_page_urls'
    
    def test_custom_results_per_page(self):
        response = self.client.get('/search/', {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['paginator'].per_page, 1)
        
        response = self.client.get('/search2/', {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['paginator'].per_page, 2)


class FacetedSearchViewTestCase(TestCase):
    def setUp(self):
        super(FacetedSearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(FacetedSearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_faceted_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['facets'], {})
    
    def test_empty_results(self):
        fsv = FacetedSearchView()
        fsv.request = HttpRequest()
        fsv.form = fsv.build_form()
        self.assert_(isinstance(fsv.get_results(), EmptySearchQuerySet))


class BasicSearchViewTestCase(TestCase):
    def setUp(self):
        super(BasicSearchViewTestCase, self).setUp()
        mock_index_site = SearchSite()
        mock_index_site.register(MockModel)
        mock_index_site.register(AnotherMockModel)
        
        # Stow.
        self.old_site = haystack.site
        haystack.site = mock_index_site
        
        self.old_engine = getattr(settings, 'HAYSTACK_SEARCH_ENGINE')
        settings.HAYSTACK_SEARCH_ENGINE = 'dummy'
    
    def tearDown(self):
        haystack.site = self.old_site
        settings.HAYSTACK_SEARCH_ENGINE = self.old_engine
        super(BasicSearchViewTestCase, self).tearDown()
    
    def test_search_no_query(self):
        response = self.client.get(reverse('haystack_basic_search'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_query(self):
        response = self.client.get(reverse('haystack_basic_search'), {'q': 'hello world'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(type(response.context[-1]['form']), ModelSearchForm)
        self.assertEqual(len(response.context[-1]['page'].object_list), 1)
        self.assertEqual(response.context[-1]['page'].object_list[0].content_type(), 'haystack.dummymodel')
        self.assertEqual(response.context[-1]['page'].object_list[0].pk, 1)
        self.assertEqual(response.context[-1]['query'], 'hello world')
    
    def test_invalid_page(self):
        response = self.client.get(reverse('haystack_basic_search'), {'q': 'hello world', 'page': '165233'})
        self.assertEqual(response.status_code, 404)
