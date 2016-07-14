# encoding: utf-8

import unittest
import warnings

from django.conf import settings

from haystack.utils import log as logging

warnings.simplefilter('ignore', Warning)

def setup():
    log = logging.getLogger('haystack')
    try:
        import elasticsearch
        if not ((1, 0, 0) <= elasticsearch.__version__ < (2, 0, 0)):
            raise ImportError
        from elasticsearch import Elasticsearch, ElasticsearchException
    except ImportError:
        self.log.error("elasticsearch-py not installed.", exc_info=True)
        raise unittest.SkipTest("elasticsearch-py not installed.")

    es = Elasticsearch(settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'])
    try:
        es.info()
    except ElasticsearchException as e:
        self.log.error("elasticsearch not running on %r" % \
                       settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'], exc_info=True)
        raise unittest.SkipTest("elasticsearch not running on %r" % \
                                settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'], e)
