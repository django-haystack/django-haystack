# -*- coding: utf-8 -*-
"""Health checks, smoke tests, diagnoses."""
from django.conf import settings

from haystack import connections


def smoketest():
    """Check haystack status."""
    # Check settings.
    assert 'haystack' in settings.INSTALLED_APPS
    # Check connections.
    for connection in connections:
        assert connection.smoketest() is True
