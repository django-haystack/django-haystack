# encoding: utf-8

import unittest
import warnings

from django.conf import settings


warnings.simplefilter('ignore', Warning)

def setup():
    try:
        from elasticsearch import Elasticsearch, ElasticsearchException
    except ImportError:
        raise unittest.SkipTest("elasticsearch-py not installed.")

    es = Elasticsearch(settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'])
    try:
        es.info()
    except ElasticsearchException as e:
        raise unittest.SkipTest("elasticsearch not running on %r" % settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'], e)

