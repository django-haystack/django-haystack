from importlib.metadata import PackageNotFoundError, version

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from packaging.version import Version

from haystack.constants import DEFAULT_ALIAS
from haystack.utils import loading

__author__ = "Daniel Lindsley"

try:
    __version__ = version("django-haystack")
    version_info = Version(__version__)
except PackageNotFoundError:
    __version__ = "0.0.dev0"
    version_info = Version(__version__)

# Help people clean up from 1.X.
if hasattr(settings, "HAYSTACK_SITECONF"):
    raise ImproperlyConfigured(
        "The HAYSTACK_SITECONF setting is no longer used & can be removed."
    )
if hasattr(settings, "HAYSTACK_SEARCH_ENGINE"):
    raise ImproperlyConfigured(
        "The HAYSTACK_SEARCH_ENGINE setting has been replaced with HAYSTACK_CONNECTIONS."
    )
if hasattr(settings, "HAYSTACK_ENABLE_REGISTRATIONS"):
    raise ImproperlyConfigured(
        "The HAYSTACK_ENABLE_REGISTRATIONS setting is no longer used & can be removed."
    )
if hasattr(settings, "HAYSTACK_INCLUDE_SPELLING"):
    raise ImproperlyConfigured(
        "The HAYSTACK_INCLUDE_SPELLING setting is now a per-backend setting"
        " & belongs in HAYSTACK_CONNECTIONS."
    )


# Check the 2.X+ bits.
if not hasattr(settings, "HAYSTACK_CONNECTIONS"):
    raise ImproperlyConfigured("The HAYSTACK_CONNECTIONS setting is required.")
if DEFAULT_ALIAS not in settings.HAYSTACK_CONNECTIONS:
    raise ImproperlyConfigured(
        "The default alias '%s' must be included in the HAYSTACK_CONNECTIONS setting."
        % DEFAULT_ALIAS
    )

# Load the connections.
connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)

# Just check HAYSTACK_ROUTERS setting validity, routers will be loaded lazily
if hasattr(settings, "HAYSTACK_ROUTERS"):
    if not isinstance(settings.HAYSTACK_ROUTERS, (list, tuple)):
        raise ImproperlyConfigured(
            "The HAYSTACK_ROUTERS setting must be either a list or tuple."
        )

# Load the router(s).
connection_router = loading.ConnectionRouter()


# Per-request, reset the ghetto query log.
# Probably not extraordinarily thread-safe but should only matter when
# DEBUG = True.
def reset_search_queries(**kwargs):
    for conn in connections.all():
        if conn:
            conn.reset_queries()


if settings.DEBUG:
    from django.core import signals as django_signals

    django_signals.request_started.connect(reset_search_queries)
