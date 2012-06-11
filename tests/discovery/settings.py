import tempfile
from core.settings import *

INSTALLED_APPS += [
    'discovery',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': tempfile.mkdtemp(suffix='test_whoosh_query'),
        'INCLUDE_SPELLING': True,
    },
}
