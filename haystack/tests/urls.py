from django.conf.urls.defaults import *
from haystack.backends.dummy import SearchBackend, SearchQuery
from haystack.query import SearchQuerySet
from haystack.views import SearchView


sq = SearchQuery(backend=SearchBackend())
sqs = SearchQuerySet(query=sq)


urlpatterns = patterns('haystack.views',
    url(r'^$', SearchView(searchqueryset=sqs), name='haystack_search'),
)
