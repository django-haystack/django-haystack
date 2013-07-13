import warnings
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.views.generic.list import MultipleObjectMixin, ListView
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from haystack.forms import ModelSearchForm, FacetedSearchForm
from haystack.query import EmptySearchQuerySet


RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 20)

class SearchMixin(MultipleObjectMixin):
    template_name = 'search/search.html'
    load_all = True
    form_class = ModelSearchForm
    searchqueryset = None
    context_class = RequestContext
    query = ''
    results = EmptySearchQuerySet()
    request = None
    form = None
    form_kwargs = {}
    paginator_class = Paginator
    paginate_by = RESULTS_PER_PAGE
    paginate_orphans = 0
    context_object_name = 'results'

    # required for django<1.6
    def get_paginate_orphans(self):
        return self.paginate_orphans

    def build_form(self, form_kwargs=None):
        """
        Instantiates the form the class should use to process the search query.
        """
        data = None
        kwargs = {
            'load_all': self.load_all,
        }
        if form_kwargs:
            kwargs.update(form_kwargs)

        if len(self.request.GET):
            data = self.request.GET

        if self.searchqueryset is not None:
            kwargs['searchqueryset'] = self.searchqueryset
        return self.form_class(data, **kwargs)

    def get_query(self):
        """
        Returns the queryset provided by the user.
        Returns an empty string if the queryset is invalid.
        """
        if self.form.is_valid():
            return self.form.cleaned_data['q']
        return ''

    def get_queryset(self):
        """
        Fetches the results via the form.

        Returns an empty list if there's no query to search with.
        """
        self.form = self.build_form()
        self.results = self.form.search()
        return self.results

    def get_context_data(self, **kwargs):
        kwargs.update({
            'form': self.build_form(),
            'query': self.get_query(),
            'object_list': self.get_queryset(),
            'suggestion': None
        })
        context = super(SearchMixin, self).get_context_data(**kwargs)
        if hasattr(self, 'extra_context'):
            if callable(self.extra_context):
                extra_context = self.extra_context()
            else: 
                extra_context = self.extra_context
            context.update(extra_context)
            warnings.warn("SearchView.extra_context is depricated use SearchView.get_get_context_data() instead.", PendingDeprecationWarning)
            context.update(extra_context)
        if self.results and hasattr(self.results, 'query') and self.results.query.backend.include_spelling:
            context['suggestion'] = self.form.get_suggestion()
        context['page'] = context['page_obj'] # for backward compatibility
        return self.context_class(context)

    # Depricated methods and properties for backward compatibility

    def get_results(self):
        warnings.warn("SearchView.get_results() is depricated use SearchView.get_queryset() instead.", PendingDeprecationWarning)
        return self.get_queryset()

    def build_page(self):
        queryset = self.get_queryset()
        page_size = self.get_paginate_by()
        (paginator, page, queryset, is_paginated) = self.paginate_queryset(queryset, page_size)
        warnings.warn("SearchView.build_page is depricated.", PendingDeprecationWarning)
        return (paginator, page)

    @property
    def template(self):
        warnings.warn("SearchView.template is depricated use SearchView.template_name instead.", PendingDeprecationWarning)
        return self.template_name

    @template.setter
    def template(self, value):
        warnings.warn("SearchView.template is depricated use SearchView.template_name instead.", PendingDeprecationWarning)
        self.template_name = value

    @template.deleter
    def template(self):
        warnings.warn("SearchView.template is depricated use SearchView.template_name instead.", PendingDeprecationWarning)
        del self.template_name

    @property
    def results_per_page(self):
        warnings.warn("SearchView.results_per_page is depricated use SearchView.paginate_by instead.", PendingDeprecationWarning)
        return self.paginate_by

    @results_per_page.setter
    def results_per_page(self, value):
        warnings.warn("SearchView.results_per_page is depricated use SearchView.paginate_by instead.", PendingDeprecationWarning)
        self.paginate_by = value

    @results_per_page.deleter
    def results_per_page(self):
        warnings.warn("SearchView.results_per_page is depricated use SearchView.paginate_by instead.", PendingDeprecationWarning)
        del self.paginate_by

class FacetedSearchMixin(SearchMixin):
    form_class = FacetedSearchForm

    def build_form(self, form_kwargs=None):
        if form_kwargs is None:
            form_kwargs = {}
        # This way the form can always receive a list containing zero or more
        # facet expressions:
        form_kwargs['selected_facets'] = self.request.GET.getlist("selected_facets")
        return super(FacetedSearchView, self).build_form(form_kwargs)

    def get_context_data(self, **kwargs):
        context = super(FacetSearchMixin, self).get_context_data(**kwargs)
        context['facets'] = self.results.facet_counts()
        return context

class GenericSearchView(SearchMixin, ListView):
    pass

SearchView = GenericSearchView.as_view


class GenericFacetedSearchView(FacetedSearchMixin, ListView):
    pass

FacetedSearchView = GenericFacetedSearchView.as_view


def search_view_factory(view_class=SearchView, *args, **kwargs):
    def search_view(request):
        return view_class(*args, **kwargs)(request)
    return search_view


def basic_search(request, template='search/search.html', load_all=True, form_class=ModelSearchForm, searchqueryset=None, context_class=RequestContext, extra_context=None, results_per_page=None):
    """
    A more traditional view that also demonstrate an alternative
    way to use Haystack.

    Useful as an example of for basing heavily custom views off of.

    Also has the benefit of thread-safety, which the ``SearchView`` class may
    not be.

    Template:: ``search/search.html``
    Context::
        * form
          An instance of the ``form_class``. (default: ``ModelSearchForm``)
        * page
          The current page of search results.
        * paginator
          A paginator instance for the results.
        * query
          The query received by the form.
    """
    query = ''
    results = EmptySearchQuerySet()

    if request.GET.get('q'):
        form = form_class(request.GET, searchqueryset=searchqueryset, load_all=load_all)

        if form.is_valid():
            query = form.cleaned_data['q']
            results = form.search()
    else:
        form = form_class(searchqueryset=searchqueryset, load_all=load_all)

    paginator = Paginator(results, results_per_page or RESULTS_PER_PAGE)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("No such page of results!")

    context = {
        'form': form,
        'page': page,
        'paginator': paginator,
        'query': query,
        'suggestion': None,
    }

    if results.query.backend.include_spelling:
        context['suggestion'] = form.get_suggestion()

    if extra_context:
        context.update(extra_context)

    return render_to_response(template, context, context_instance=context_class(request))
