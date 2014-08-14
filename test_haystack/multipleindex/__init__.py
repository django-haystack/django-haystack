import haystack
from haystack.signals import RealtimeSignalProcessor

from django.db.models import signals

from ..utils import check_solr

_old_sp = None
def setup():
    check_solr()
    global _old_sp
    _old_sp = haystack.signal_processor
    haystack.signal_processor = RealtimeSignalProcessor(haystack.connections, haystack.connection_router)

def teardown():
    haystack.signal_processor = _old_sp
    signals.post_save.receivers = []
    signals.post_delete.receivers = []
    
