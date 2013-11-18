from settings import *

INSTALLED_APPS += [
    'elasticsearch_tests',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'test_default',
        'INCLUDE_SPELLING': True,
    },
}
