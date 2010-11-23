from settings import *

INSTALLED_APPS += [
    'overrides',
]

HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://localhost:9001/solr/test_default'
HAYSTACK_INCLUDE_SPELLING = True

HAYSTACK_ID_FIELD = 'my_id'
HAYSTACK_DJANGO_CT_FIELD = 'my_django_ct'
HAYSTACK_DJANGO_ID_FIELD = 'my_django_id'
