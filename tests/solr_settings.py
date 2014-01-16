from settings import *

INSTALLED_APPS += [
    'solr_tests',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:8983/solr',
        'INCLUDE_SPELLING': True,
    },
}
