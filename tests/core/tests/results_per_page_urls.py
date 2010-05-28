from django.conf.urls.defaults import *
from haystack.views import SearchView


class CustomPerPage(SearchView):
    results_per_page = 1


urlpatterns = patterns('haystack.views',
    url(r'^search/$', CustomPerPage(load_all=False), name='haystack_search'),
    url(r'^search2/$', CustomPerPage(load_all=False, results_per_page=2), name='haystack_search'),
)
