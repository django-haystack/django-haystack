import warnings

from django.conf import settings
from django.utils.unittest import SkipTest

warnings.simplefilter('ignore', Warning)

def setup():
    try:
        from elasticsearch import Elasticsearch, ElasticsearchException
    except ImportError:
        raise SkipTest("elasticsearch-py not installed.")

    es = Elasticsearch(settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'])
    try:
        es.info()
    except ElasticsearchException as e:
        raise SkipTest("elasticsearch not running on %r" % settings.HAYSTACK_CONNECTIONS['elasticsearch']['URL'], e)

