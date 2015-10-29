# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import os

from django.conf import settings

SECRET_KEY = 'CHANGE ME'

# All the normal settings apply. What's included here are the bits you'll have
# to customize.

# Add Haystack to INSTALLED_APPS. You can do this by simply placing in your list.
INSTALLED_APPS = settings.INSTALLED_APPS + (
    'haystack',
)


HAYSTACK_CONNECTIONS = {
    'default': {
        # For Solr:
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://localhost:9001/solr/example',
        'TIMEOUT': 60 * 5,
        'INCLUDE_SPELLING': True,
    },
    'elasticsearch': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://localhost:9200',
        'INDEX_NAME': 'example_project'
    },
    'whoosh': {
        # For Whoosh:
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
        'INCLUDE_SPELLING': True,
    },
    'simple': {
        # For Simple:
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
    # 'xapian': {
    #     # For Xapian (requires the third-party install):
    #     'ENGINE': 'xapian_backend.XapianEngine',
    #     'PATH': os.path.join(os.path.dirname(__file__), 'xapian_index'),
    # }
}
