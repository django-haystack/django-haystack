from haystack.query import SearchQuerySet
from django.shortcuts import render_to_response
from django.template import RequestContext
from forms import RestaurantSearchForm


def search(request):
    context = {}
    form = RestaurantSearchForm()
    if request.GET.get('latitude') and \
            request.GET.get('longitude') and \
            request.GET.get('radius'):
        form = RestaurantSearchForm(request.GET)
        if form.is_valid():
            sqs = SearchQuerySet().\
                spatial(lat=float(request.GET['latitude']), 
                        lng=float(request.GET['longitude']), 
                        # sfield = the field from searchindex which contains the lat/lon
                        sfield='geocode', 
                        radius=float(request.GET['radius']), 
                        sort_by_distance=True, 
                        sort_order='desc')
            context.update({'results': sqs})
    context.update({'form': form})
    return render_to_response('search.html', context,
                              RequestContext(request))
