from django.conf.urls.defaults import *
from haystack.backends.dummy_backend import SearchBackend, SearchQuery
from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView, FacetedSearchView


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)


urlpatterns += patterns('haystack.views',
    url(r'^$', SearchView(load_all=False), name='haystack_search'),
    url(r'^faceted/$', FacetedSearchView(searchqueryset=SearchQuerySet().facet('author'), form_class=FacetedSearchForm), name='haystack_faceted_search'),
    url(r'^basic/$', 'basic_search', {'load_all': False}, name='haystack_basic_search'),
)
