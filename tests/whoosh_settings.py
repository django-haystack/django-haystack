import os
from settings import *

HAYSTACK_SEARCH_ENGINE = 'whoosh'
HAYSTACK_WHOOSH_PATH = os.path.join('tmp', 'test_whoosh_query')
