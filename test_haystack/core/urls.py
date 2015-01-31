from django.conf.urls import include, patterns, url
from django.contrib import admin

from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import FacetedSearchView, SearchView

admin.autodiscover()


urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)


urlpatterns += patterns('haystack.views',
    url(r'^$', SearchView(load_all=False), name='haystack_search'),
    url(r'^faceted/$', FacetedSearchView(searchqueryset=SearchQuerySet().facet('author'), form_class=FacetedSearchForm), name='haystack_faceted_search'),
    url(r'^basic/$', 'basic_search', {'load_all': False}, name='haystack_basic_search'),
)

urlpatterns += patterns('app-without-models',
    url(r'', include('test_haystack.test_app_without_models.urls', namespace='app-without-models')),
)
