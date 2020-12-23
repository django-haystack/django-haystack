# encoding: utf-8
from test_haystack.discovery.models import Bar, Foo

from haystack import indexes


class FooIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr="body")

    def get_model(self):
        return Foo


class BarIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)

    def get_model(self):
        return Bar
