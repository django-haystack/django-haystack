from django.conf.urls.defaults import *
from haystack.backends.dummy import SearchBackend, SearchQuery
from haystack.views import SearchView


import haystack
haystack.autodiscover()


urlpatterns = patterns('haystack.views',
    url(r'^$', SearchView(), name='haystack_search'),
)
