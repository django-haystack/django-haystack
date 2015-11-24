# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack import indexes

from .models import MicroBlogPost


class MicroBlogSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=False, model_attr='text')

    def get_model(self):
        return MicroBlogPost
