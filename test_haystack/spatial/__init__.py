from django.conf import settings

from unittest import SkipTest

def setup():
    try:
        from pysolr import Solr, SolrError
    except ImportError:
        raise SkipTest("pysolr  not installed.")

    solr = Solr(settings.HAYSTACK_CONNECTIONS['solr']['URL'])
    try:
        solr.search('*:*')
    except SolrError as e:
        raise SkipTest("solr not running on %r" % settings.HAYSTACK_CONNECTIONS['solr']['URL'], e)

