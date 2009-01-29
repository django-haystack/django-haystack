from django.conf.urls.defaults import *
from djangosearch.views import SearchView


urlpatterns = patterns('djangosearch.views',
    url(r'^$', SearchView, name='djangosearch_search'),
)
