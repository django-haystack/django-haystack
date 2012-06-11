import logging
from django.core import signals
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import LazyObject

__author__ = 'Daniel Lindsley'
__version__ = (2, 0, 0, 'beta')


# Setup default logging.
log = logging.getLogger('haystack')
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
log.addHandler(stream)


class LazyDict(LazyObject):

    def __getitem__(self, index):
        if self._wrapped is None:
            self._setup()
        return self._wrapped.__getitem__(index)

    def __setitem__(self, index, value):
        if self._wrapped is None:
            self._setup()
        self._wrapped[index] = value


class LazyConnectionHandler(LazyDict):

    def reset_search_queries(self, **kwargs):
        for conn in self._wrapped.all():
            conn.reset_queries()

    def _setup(self):
        from django.conf import settings
        from haystack.utils import loading
        # Load the connections.
        self._wrapped = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)

        # Per-request, reset the ghetto query log.
        # Probably not extraordinarily thread-safe but should only matter when
        # DEBUG = True.
        if settings.DEBUG:
            signals.request_started.connect(self.reset_search_queries)


class LazyConnectionRouter(LazyDict):

    def _setup(self):
        from django.conf import settings
        from haystack.utils import loading
        if hasattr(settings, 'HAYSTACK_ROUTERS'):
            if not isinstance(settings.HAYSTACK_ROUTERS, (list, tuple)):
                raise ImproperlyConfigured("The HAYSTACK_ROUTERS setting must be either a list or tuple.")

            connection_router = loading.ConnectionRouter(settings.HAYSTACK_ROUTERS)
        else:
            connection_router = loading.ConnectionRouter()
        self._wrapped = connection_router


# Loads the connection handler
connections = LazyConnectionHandler()

# Load the router(s).
connection_router = LazyConnectionRouter()
