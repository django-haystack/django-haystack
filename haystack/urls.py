try:
    from django.conf.urls import *
except ImportError:
    from django.conf.urls.defaults import *
from haystack.views import SearchView


urlpatterns = patterns('haystack.views',
    url(r'^$', SearchView(), name='haystack_search'),
)
