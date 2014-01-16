import warnings
warnings.simplefilter('ignore', Warning)

from django.conf import settings

from core.tests.test_backends import *
from core.tests.test_fields import *
from core.tests.test_forms import *
from core.tests.test_indexes import *
from core.tests.test_inputs import *
from core.tests.test_loading import *
from core.tests.test_models import *
from core.tests.test_query import *
from core.tests.test_templatetags import *
from core.tests.test_views import *
from core.tests.test_utils import *
from core.tests.test_management_commands import *
from core.tests.test_managers import *
