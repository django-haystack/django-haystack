from tempfile import mkdtemp
from settings import *

INSTALLED_APPS += [
    'multipleindex',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9001/solr',
    },
    'whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='haystack-multipleindex-whoosh-tests-'),
        'EXCLUDED_INDEXES': ['multipleindex.search_indexes.BarIndex'],
    },
}

