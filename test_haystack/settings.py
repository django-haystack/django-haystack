import os
from tempfile import mkdtemp

SECRET_KEY = "Please do not spew DeprecationWarnings"

# Haystack settings for running tests.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'haystack_tests.db',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'haystack',

    'test_haystack.discovery',
    'test_haystack.core',
    'test_haystack.spatial',
    'test_haystack.multipleindex',

    # This app exists to confirm that nothing breaks when INSTALLED_APPS has an app without models.py
    # which is common in some cases for things like admin extensions, reporting, etc.
    'test_haystack.test_app_without_models',

]

SITE_ID = 1
ROOT_URLCONF = 'test_haystack.core.urls'

HAYSTACK_ROUTERS = ['haystack.routers.DefaultRouter', 'test_haystack.multipleindex.routers.MultipleIndexRouter']

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'test_haystack.mocks.MockEngine',
    },
    'whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='test_whoosh_query'),
        'INCLUDE_SPELLING': True,
    },
    'filtered_whoosh': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='haystack-multipleindex-filtered-whoosh-tests-'),
        'EXCLUDED_INDEXES': ['test_haystack.multipleindex.search_indexes.BarIndex'],
    },
    'elasticsearch': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': '127.0.0.1:9200/',
        'INDEX_NAME': 'test_default',
        'INCLUDE_SPELLING': True,
    },
    'simple': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
    'solr': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9001/solr/',
        'INCLUDE_SPELLING': True,
    },
}

SITE_ID = 1

MIDDLEWARE_CLASSES = ('django.middleware.common.CommonMiddleware',
                      'django.contrib.sessions.middleware.SessionMiddleware',
                      'django.middleware.csrf.CsrfViewMiddleware',
                      'django.contrib.auth.middleware.AuthenticationMiddleware',
                      'django.contrib.messages.middleware.MessageMiddleware')