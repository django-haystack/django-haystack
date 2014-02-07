# -*- coding: utf-8 -*-
"""Health checks, smoke tests, diagnoses."""
from django.conf import settings

from haystack import connections


def smoketest():
    """Check haystack status."""
    # Check settings.
    assert 'haystack' in settings.INSTALLED_APPS
    # Check connections.
    for connection_id in settings.HAYSTACK_CONNECTIONS.keys():
        backend = connections[connection_id]
        assert backend._backend.conn.smoketest() is True
