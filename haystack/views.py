from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from haystack.forms import ModelSearchForm


RESULTS_PER_PAGE = getattr(settings, 'SEARCH_RESULTS_PER_PAGE', 20)


class SearchView(object):
    def __init__(self, template=None, load_all=True, form_class=ModelSearchForm, searchqueryset=None, context_class=RequestContext):
        self.load_all = load_all
        self.template = template or 'search/search.html'
        self.form_class = form_class
        self.context_class = context_class
        self.searchqueryset = searchqueryset

    def __name__(self):
        return "SearchView"

    def __call__(self, request):
        if self.searchqueryset is None:
            form = self.form_class(request.GET)
        else:
            form = self.form_class(request.GET, searchqueryset=self.searchqueryset)
        
        query = ''
        results = []
        facets = {}
        
        if form.is_valid():
            query = form.cleaned_data['query']
            
            if query:
                results = form.search()
            else:
                results = []
        
        paginator = Paginator(results, RESULTS_PER_PAGE)
        
        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except ValueError:
            raise Http404
        
        return render_to_response(self.template, {
            'query': query,
            'form': form,
            'page': page,
            'paginator': paginator,
        }, context_instance=self.context_class(request))


class FacetedSearchView(object):
    def __name__(self):
        return "FacetedSearchView"

    def __call__(self, request):
        if self.searchqueryset is None:
            form = self.form_class(request.GET)
        else:
            form = self.form_class(request.GET, searchqueryset=self.searchqueryset)
        
        query = ''
        results = []
        facets = {}
        
        if form.is_valid():
            query = form.cleaned_data['query']
            
            if query:
                results = form.search()
                facets = results.facet_counts()
            else:
                results = []
        
        paginator = Paginator(results, RESULTS_PER_PAGE)
        
        try:
            page = paginator.page(int(request.GET.get('page', 1)))
        except ValueError:
            raise Http404
        
        return render_to_response(self.template, {
            'query': query,
            'form': form,
            'facets': facets,
            'page': page,
            'paginator': paginator,
        }, context_instance=self.context_class(request))
