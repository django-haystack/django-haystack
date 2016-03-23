# -*- coding: utf-8 -*-
import warnings

from django.conf import settings

from ..utils import unittest

warnings.simplefilter('ignore', Warning)


def setup():
    try:
        from elasticsearch import Elasticsearch, exceptions
    except ImportError:
        raise unittest.SkipTest("elasticsearch-py not installed.")

    url = settings.HAYSTACK_CONNECTIONS['elasticsearch2']['URL']
    es = Elasticsearch(url)
    try:
        es.info()
    except exceptions.ConnectionError as e:
        raise unittest.SkipTest("elasticsearch not running on %r" % url, e)
