from settings import *

INSTALLED_APPS += [
    'spatial',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        # Solr 3.5
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9001/solr/test_spatial',
        'DISTANCE_AVAILABLE': False,
    },
    'solr_native_distance': {
        # Solr 4.X+
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9002/solr/',
        # See ``haystack/backends/solr_backend.py`` for details on why not.
        # 'DISTANCE_AVAILABLE': True,
    },
    # 'elasticsearch': {
    #     # Elasticsearch
    #     'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
    #     'URL': 'http://localhost:9001/solr/test_spatial',
    #     'DISTANCE_AVAILABLE': False,
    # },
}
