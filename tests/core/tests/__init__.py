import warnings
warnings.simplefilter('ignore', Warning)

from core.tests.fields import *
from core.tests.indexes import *
from core.tests.models import *
from core.tests.query import *
from core.tests.sites import *
from core.tests.views import *
from core.tests.backends.solr_query import *
from core.tests.backends.whoosh_query import *

# Backends.
# Uncomment as needed to test new versions of libraries or to ensure
# compatibility.
from core.tests.backends.solr_backend import *
from core.tests.backends.whoosh_backend import *
