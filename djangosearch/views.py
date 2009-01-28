from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext as Context
from djangosearch import search
from djangosearch.forms import ModelSearchForm


RESULTS_PER_PAGE = getattr(settings, 'SEARCH_RESULTS_PER_PAGE', 20)


# DRL_FIXME: Split into lots of calls for easy extension.
class SearchView(object):
    def __init__(self, template=None, load_all=True):
        self.load_all = load_all
        self.template = template or 'search/search.html'

    def __name__(self):
        return "SearchView"

    def __call__(self, request):
        form = self.search_form(request)
        
        if not form.is_valid():
            # DRL_FIXME: Is this really what we want? Wouldn't returning no results be better?
            raise Exception(form.errors)
        
        query = form.cleaned_data['query']
        search_models = form.get_models()

        try:
            page = request.GET.get('page', 1)
            page_number = int(page)
        except ValueError:
            raise Http404

        offset = (page_number - 1) * RESULTS_PER_PAGE
        results = search(query, models=search_models, limit=RESULTS_PER_PAGE, offset=offset)
        
        # DRL_FIXME: What does the following comment even mean?
        # XXX: implement load_all

        paginator = Paginator(results, RESULTS_PER_PAGE)
        context = Context(request, {
            'query': query,
            'form': form,
            'page': paginator.page(page_number),
            'paginator' : paginator

        })
        return render_to_response(self.template, context_instance=context)

    def search_form(self, request):
        return ModelSearchForm(request.GET)
