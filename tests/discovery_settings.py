import os
from settings import *

INSTALLED_APPS += [
    'discovery',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join('tmp', 'test_whoosh_query'),
        'INCLUDE_SPELLING': True,
    },
}
