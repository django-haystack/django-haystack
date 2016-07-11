# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from test_haystack.discovery.models import Bar

from haystack import indexes


class BarIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)

    def get_model(self):
        return Bar
