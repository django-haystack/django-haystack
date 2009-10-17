# All the normal settings apply. What's included here are the bits you'll have
# to customize.

# Add Haystack to INSTALLED_APPS. You can do this by simply placing in your list.
INSTALLED_APPS = INSTALLED_APPS + [
    'haystack',
]

# Required and specific to where you place the file.
HAYSTACK_SITECONF = 'example_project.search_sites'

# Optional Haystack settings.
# See `docs/settings.rst` for a complete list.
HAYSTACK_INCLUDE_SPELLING = True


# For Solr:
HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://localhost:9001/solr/example'
HAYSTACK_SOLR_TIMEOUT = 60 * 5


# For Whoosh:
# import os
# HAYSTACK_SEARCH_ENGINE = 'whoosh'
# HAYSTACK_WHOOSH_PATH = os.path.join(os.path.dirname(__file__), 'whoosh_index')


# For Xapian (requires the third-party install):
# import os
# HAYSTACK_SEARCH_ENGINE = 'xapian'
# HAYSTACK_XAPIAN_PATH = os.path.join(os.path.dirname(__file__), 'xapian_index')
