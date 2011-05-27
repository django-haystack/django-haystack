import os
from settings import *

INSTALLED_APPS += [
    'multipleindex',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9001/solr/test_default',
    },
    'whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join('tmp', 'test_whoosh_query'),
    },
}

HAYSTACK_EXCLUDED_INDEXES = [
    'multipleindex.search_indexes.BaseIndex',
]

