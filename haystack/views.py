from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from haystack.forms import ModelSearchForm


RESULTS_PER_PAGE = getattr(settings, 'HAYSTACK_SEARCH_RESULTS_PER_PAGE', 20)


class SearchView(object):
    template = 'search/search.html'
    extra_context = {}
    query = ''
    results = []
    request = None
    form = None
    
    def __init__(self, template=None, load_all=True, form_class=ModelSearchForm, searchqueryset=None, context_class=RequestContext):
        self.load_all = load_all
        self.form_class = form_class
        self.context_class = context_class
        self.searchqueryset = searchqueryset
        
        if template:
            self.template = template

    def __name__(self):
        return "SearchView"

    def __call__(self, request):
        """
        Generates the actual response to the search.
        
        Relies on internal, overridable methods to construct the response.
        """
        self.request = request
        
        self.form = self.build_form()
        self.query = self.get_query()
        self.results = self.get_results()
        
        return self.create_response()
    
    def build_form(self):
        """
        Instantiates the form the class should use to process the search query.
        """
        if self.searchqueryset is None:
            return self.form_class(self.request.GET, load_all=self.load_all)
        
        return self.form_class(self.request.GET, searchqueryset=self.searchqueryset, load_all=self.load_all)
    
    def get_query(self):
        """
        Returns the query provided by the user.
        
        Returns an empty string if the query is invalid.
        """
        if self.form.is_valid():
            return self.form.cleaned_data['q']
        
        return ''
    
    def get_results(self):
        """
        Fetches the results via the form.
        
        Returns an empty list if there's no query to search with.
        """
        if self.query:
            return self.form.search()
        
        return []
    
    def build_page(self):
        """
        Paginates the results appropriately.
        
        In case someone does not want to use Django's built-in pagination, it
        should be a simple matter to override this method to do what they would
        like.
        """
        paginator = Paginator(self.results, RESULTS_PER_PAGE)
        
        try:
            page = paginator.page(self.request.GET.get('page', 1))
        except InvalidPage:
            raise Http404
        
        return (paginator, page)
    
    def extra_context(self):
        """
        Allows the addition of more context variables as needed.
        
        Must return a dictionary.
        """
        return {}
    
    def create_response(self):
        """
        Generates the actual HttpResponse to send back to the user.
        """
        (paginator, page) = self.build_page()
        
        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
        }
        context.update(self.extra_context())
        
        return render_to_response(self.template, context, context_instance=self.context_class(self.request))


class FacetedSearchView(SearchView):
    def __name__(self):
        return "FacetedSearchView"
    
    def extra_context(self):
        extra = super(FacetedSearchView, self).extra_context()
        
        if self.results == []:
            extra['facets'] = self.form.search().facet_counts()
        else:
            extra['facets'] = self.results.facet_counts()
        
        return extra
