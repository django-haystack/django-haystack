# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.test.client import RequestFactory
from django.test.testcases import TestCase

from haystack.forms import ModelSearchForm
from haystack.generic_views import SearchView


class GenericSearchViewsTestCase(TestCase):
    """Test case for the generic search views."""

    def setUp(self):
        super(GenericSearchViewsTestCase, self).setUp()
        self.query = 'haystack'
        self.request = self.get_request(
            url='/some/random/url?q={0}'.format(self.query)
        )

    def test_get_form_kwargs(self):
        """Test getting the search view form kwargs."""
        v = SearchView()
        v.request = self.request

        form_kwargs = v.get_form_kwargs()
        self.assertEqual(form_kwargs.get('data').get('q'), self.query)
        self.assertEqual(form_kwargs.get('initial'), {})
        self.assertTrue('searchqueryset' in form_kwargs)

    def test_search_view_response(self):
        """Test the generic SearchView response."""
        response = SearchView.as_view()(request=self.request)

        context = response.context_data
        self.assertEqual(context['query'], self.query)
        self.assertEqual(context.get('view').__class__, SearchView)
        self.assertEqual(context.get('form').__class__, ModelSearchForm)
        self.assertIn('page_obj', context)
        self.assertNotIn('page', context)

    def test_search_view_form_valid(self):
        """Test the generic SearchView form is valid."""
        v = SearchView()
        v.kwargs = {}
        v.request = self.request

        form = v.get_form(v.get_form_class())
        response = v.form_valid(form)
        context = response.context_data

        self.assertEqual(context['query'], self.query)

    def test_search_view_form_invalid(self):
        """Test the generic SearchView form is invalid."""
        v = SearchView()
        v.kwargs = {}
        v.request = self.request

        form = v.get_form(v.get_form_class())
        response = v.form_invalid(form)
        context = response.context_data

        self.assertTrue('query' not in context)

    def get_request(self, url, method='get', data=None, **kwargs):
        """Gets the request object for the view.

        :param url: a mock url to use for the request
        :param method: the http method to use for the request ('get', 'post',
            etc).
        """
        factory = RequestFactory()
        factory_func = getattr(factory, method)

        request = factory_func(url, data=data or {}, **kwargs)
        return request
