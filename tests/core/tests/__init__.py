import warnings
warnings.simplefilter('ignore', Warning)

from django.conf import settings

from core.tests.backends import *
from core.tests.fields import *
from core.tests.forms import *
from core.tests.indexes import *
from core.tests.inputs import *
from core.tests.loading import *
from core.tests.models import *
from core.tests.query import *
from core.tests.templatetags import *
from core.tests.views import *
from core.tests.utils import *
from core.tests.management_commands import *
from core.tests.managers import *
