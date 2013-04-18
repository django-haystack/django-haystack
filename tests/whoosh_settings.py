from tempfile import mkdtemp
import os
from settings import *

INSTALLED_APPS += [
    'whoosh_tests',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': mkdtemp(prefix='haystack-whoosh-tests-'),
        'INCLUDE_SPELLING': True,
    },
}
