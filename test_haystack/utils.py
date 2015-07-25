# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings

import unittest


if not hasattr(unittest, 'skipIf'):
    # Some unittest features we need were introduced in Python 2.7, but we are
    # dealing with Python 2.6, so we fallback to Django's unittest2. It was
    # deprecated in Django 1.8; removed in Django 1.9 (both of which require
    # at least Python 2.7)
    from django.utils import unittest


def check_solr(using='solr'):
    try:
        from pysolr import Solr, SolrError
    except ImportError:
        raise unittest.SkipTest("pysolr  not installed.")

    solr = Solr(settings.HAYSTACK_CONNECTIONS[using]['URL'])
    try:
        solr.search('*:*')
    except SolrError as e:
        raise unittest.SkipTest("solr not running on %r" % settings.HAYSTACK_CONNECTIONS[using]['URL'], e)
