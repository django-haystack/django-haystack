# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import haystack
from haystack.signals import RealtimeSignalProcessor

from django.apps import apps

from ..utils import check_solr

_old_sp = None
def setup():
    check_solr()
    global _old_sp
    config = apps.get_app_config('haystack')
    _old_sp = config.signal_processor
    config.signal_processor = RealtimeSignalProcessor(haystack.connections, haystack.connection_router)

def teardown():
    config = apps.get_app_config('haystack')
    config.signal_processor.teardown()
    config.signal_processor = _old_sp
