from __future__ import unicode_literals

import logging

from django.apps import AppConfig
from django.conf import settings

from haystack import connection_router, connections
from haystack.utils import loading


class HaystackConfig(AppConfig):
    name = 'haystack'
    signal_processor = None
    stream = None

    def ready(self):
        # Setup default logging.
        log = logging.getLogger('haystack')
        self.stream = logging.StreamHandler()
        self.stream.setLevel(logging.INFO)
        log.addHandler(self.stream)

        # Setup the signal processor.
        if not self.signal_processor:
            signal_processor_path = getattr(settings, 'HAYSTACK_SIGNAL_PROCESSOR', 'haystack.signals.BaseSignalProcessor')
            signal_processor_class = loading.import_class(signal_processor_path)
            self.signal_processor = signal_processor_class(connections, connection_router)
