from django.conf.urls.defaults import *
from djangosearch.backends.dummy import SearchBackend, SearchQuery
from djangosearch.query import SearchQuerySet
from djangosearch.views import SearchView


sq = SearchQuery(backend=SearchBackend())
sqs = SearchQuerySet(query=sq)


urlpatterns = patterns('djangosearch.views',
    url(r'^$', SearchView(searchqueryset=sqs), name='djangosearch_search'),
)
