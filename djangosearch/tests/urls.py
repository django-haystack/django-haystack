from django.conf.urls.defaults import *
from djangosearch.backends.dummy import SearchBackend, SearchQuery
from djangosearch.query import BaseSearchQuerySet
from djangosearch.views import SearchView


sq = SearchQuery(backend=SearchBackend())
sqs = BaseSearchQuerySet(query=sq)


urlpatterns = patterns('djangosearch.views',
    url(r'^$', SearchView(searchqueryset=sqs), name='djangosearch_search'),
)
