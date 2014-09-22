from django.conf import settings
from django.utils.unittest import SkipTest


def check_solr(using='solr'):
    try:
        from pysolr import Solr, SolrError
    except ImportError:
        raise SkipTest("pysolr  not installed.")

    solr = Solr(settings.HAYSTACK_CONNECTIONS[using]['URL'])
    try:
        solr.search('*:*')
    except SolrError as e:
        raise SkipTest("solr not running on %r" % settings.HAYSTACK_CONNECTIONS[using]['URL'], e)
