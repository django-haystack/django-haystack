from tempfile import mkdtemp
from settings import *

INSTALLED_APPS += [
    'multipleindex',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:8983/solr',
        'EXCLUDED_INDEXES': ['multipleindex.search_indexes.BazIndex'],
    },
    'whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='haystack-multipleindex-whoosh-tests-'),
        'EXCLUDED_INDEXES': ['multipleindex.search_indexes.BarIndex',
            'multipleindex.search_indexes.BazIndex'],
    },
    'filtered_whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='haystack-multipleindex-filtered-whoosh-tests-'),
        'EXCLUDED_INDEXES': ['multipleindex.search_indexes.BarIndex'],
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

HAYSTACK_ROUTERS = ['multipleindex.routers.BazRouter', 'haystack.routers.DefaultRouter']
