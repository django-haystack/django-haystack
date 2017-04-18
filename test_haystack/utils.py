# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import inspect
import os
import sys
import string
import random

from django.conf import settings


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



def get_script_dir(follow_symlinks=True):
    return os.path.dirname(os.path.abspath(inspect.stack()[1][1]))
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
