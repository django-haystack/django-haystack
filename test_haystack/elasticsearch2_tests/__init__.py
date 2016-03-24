# -*- coding: utf-8 -*-
import warnings

from django.conf import settings

from ..utils import unittest

warnings.simplefilter('ignore', Warning)


def setup():
    try:
        import elasticsearch
        if not ((2, 0, 0) <= elasticsearch.__version__ < (3, 0, 0)):
            raise ImportError
        from elasticsearch import Elasticsearch, exceptions
    except ImportError:
        raise unittest.SkipTest("'elasticsearch>=2.0.0,<3.0.0' not installed.")

    url = settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL']
    es = Elasticsearch(url)
    try:
        es.info()
    except exceptions.ConnectionError as e:
        raise unittest.SkipTest("elasticsearch not running on %r" % url, e)
