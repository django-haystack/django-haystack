# encoding: utf-8

import warnings

warnings.simplefilter("ignore", Warning)

from ..utils import check_solr


def setup():
    check_solr()
