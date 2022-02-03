import unittest
import warnings

from django.conf import settings

from haystack.utils import log as logging

warnings.simplefilter("ignore", Warning)


def setup():
    log = logging.getLogger("haystack")
    try:
        import elasticsearch

        if not ((5, 0, 0) <= elasticsearch.__version__ < (6, 0, 0)):
            raise ImportError
        from elasticsearch import Elasticsearch, exceptions
    except ImportError:
        log.error(
            "Skipping ElasticSearch 5 tests: 'elasticsearch>=5.0.0,<6.0.0' not installed."
        )
        raise unittest.SkipTest("'elasticsearch>=5.0.0,<6.0.0' not installed.")

    url = settings.HAYSTACK_CONNECTIONS["elasticsearch"]["URL"]
    es = Elasticsearch(url)
    try:
        es.info()
    except exceptions.ConnectionError as e:
        log.error("elasticsearch not running on %r" % url, exc_info=True)
        raise unittest.SkipTest("elasticsearch not running on %r" % url, e)
