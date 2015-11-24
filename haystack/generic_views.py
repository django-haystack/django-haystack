# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.core.paginator import Paginator
from django.views.generic import FormView
from django.views.generic.edit import FormMixin
from django.views.generic.list import MultipleObjectMixin

from .forms import FacetedSearchForm, ModelSearchForm
from .query import SearchQuerySet

RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 20)


class SearchMixin(MultipleObjectMixin, FormMixin):
    """
    A mixin that allows adding in Haystacks search functionality into
    another view class.

    This mixin exhibits similar end functionality as the base Haystack search
    view, but with some important distinctions oriented around greater
    compatibility with Django's built-in class based views and mixins.

    Normal flow:

        self.request = request

        self.form = self.build_form()
        self.query = self.get_query()
        self.results = self.get_results()

        return self.create_response()

    This mixin should:

        1. Make the form
        2. Get the queryset
        3. Return the paginated queryset

    """
    template_name = 'search/search.html'
    load_all = True
    form_class = ModelSearchForm
    queryset = SearchQuerySet()
    context_object_name = None
    paginate_by = RESULTS_PER_PAGE
    paginate_orphans = 0
    paginator_class = Paginator
    page_kwarg = 'page'
    form_name = 'form'
    search_field = 'q'
    object_list = None

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = {'initial': self.get_initial()}
        if self.request.method == 'GET':
            kwargs.update({
                'data': self.request.GET,
            })
        kwargs.update({'searchqueryset': self.get_queryset()})
        return kwargs

    def form_invalid(self, form):
        context = self.get_context_data(**{
            self.form_name: form,
            'object_list': self.get_queryset()
        })
        return self.render_to_response(context)

    def form_valid(self, form):
        self.queryset = form.search()
        context = self.get_context_data(**{
            self.form_name: form,
            'query': form.cleaned_data.get(self.search_field),
            'object_list': self.queryset
        })
        return self.render_to_response(context)


class FacetedSearchMixin(SearchMixin):
    """
    A mixin that allows adding in a Haystack search functionality with search
    faceting.
    """
    form_class = FacetedSearchForm
    facet_fields = None

    def get_form_kwargs(self):
        kwargs = super(FacetedSearchMixin, self).get_form_kwargs()
        kwargs.update({
            'selected_facets': self.request.GET.getlist("selected_facets")
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(FacetedSearchMixin, self).get_context_data(**kwargs)
        context.update({'facets': self.queryset.facet_counts()})
        return context

    def get_queryset(self):
        qs = super(FacetedSearchMixin, self).get_queryset()
        for field in self.facet_fields:
            qs = qs.facet(field)
        return qs


class SearchView(SearchMixin, FormView):
    """A view class for searching a Haystack managed search index"""

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class FacetedSearchView(FacetedSearchMixin, SearchView):
    """
    A view class for searching a Haystack managed search index with
    facets
    """
    pass
