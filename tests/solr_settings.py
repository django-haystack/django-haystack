from settings import *

INSTALLED_APPS += [
    'solr_tests',
]

HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://localhost:9001/solr/test_default'
HAYSTACK_INCLUDE_SPELLING = True
