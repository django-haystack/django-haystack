import warnings
warnings.simplefilter('ignore', Warning)

from core.tests.fields import *
from core.tests.forms import *
from core.tests.indexes import *
from core.tests.models import *
from core.tests.query import *
from core.tests.sites import *
from core.tests.views import *
from core.tests.backends.solr_query import *
from core.tests.backends.whoosh_query import *

# Backends.
# Switch settings files to test the various backends.
from django.conf import settings

if settings.HAYSTACK_SEARCH_ENGINE == 'solr':
    from core.tests.backends.solr_backend import *
elif settings.HAYSTACK_SEARCH_ENGINE == 'whoosh':
    from core.tests.backends.whoosh_backend import *
