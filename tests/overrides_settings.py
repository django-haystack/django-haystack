from settings import *

INSTALLED_APPS += [
    'overrides',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:8983/solr/test_default',
        'INCLUDE_SPELLING': True,
    },
}

HAYSTACK_ID_FIELD = 'my_id'
HAYSTACK_DJANGO_CT_FIELD = 'my_django_ct'
HAYSTACK_DJANGO_ID_FIELD = 'my_django_id'
