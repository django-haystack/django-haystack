import os
from core.settings import *

INSTALLED_APPS += [
    'whoosh_tests',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join('tmp', 'test_whoosh_query'),
        'INCLUDE_SPELLING': True,
        # 'STORAGE': 'ram',
    },
}
