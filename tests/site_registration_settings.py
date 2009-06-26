import os
from settings import *

INSTALLED_APPS += [
    'site_registration',
]

ROOT_URLCONF = 'site_registration.manual_urls'

HAYSTACK_SEARCH_ENGINE = 'whoosh'
HAYSTACK_WHOOSH_PATH = os.path.join('tmp', 'test_whoosh_query')
HAYSTACK_INCLUDE_SPELLING = True
