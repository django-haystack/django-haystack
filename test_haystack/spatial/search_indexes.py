# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack import indexes

from .models import Checkin, CheckinMulti


class CheckinSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    username = indexes.CharField(model_attr='username')
    comment = indexes.CharField(model_attr='comment')
    # Again, if you were using GeoDjango, this could be just:
    #   location = indexes.LocationField(model_attr='location')
    location = indexes.LocationField(model_attr='get_location')
    created = indexes.DateTimeField(model_attr='created')

    def get_model(self):
        return Checkin

    def prepare_text(self, obj):
        # Because I don't feel like creating a template just for this.
        return '\n'.join([obj.comment, obj.username])


class CheckinMultiSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    username = indexes.CharField(model_attr='username')
    comment = indexes.CharField(model_attr='comment')
    # Again, if you were using GeoDjango, this could be just:
    #   location = indexes.MultiLocationField(model_attr='multi_locations')
    location = indexes.MultiLocationField(model_attr='get_multi_locations')
    created = indexes.DateTimeField(model_attr='created')

    def get_model(self):
        return CheckinMulti

    def prepare_text(self, obj):
        # Because I don't feel like creating a template just for this.
        return '\n'.join([obj.comment, obj.username])
