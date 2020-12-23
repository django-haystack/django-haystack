# encoding: utf-8
from haystack import indexes

from .models import Checkin


class CheckinSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    username = indexes.CharField(model_attr="username")
    comment = indexes.CharField(model_attr="comment")
    # Again, if you were using GeoDjango, this could be just:
    #   location = indexes.LocationField(model_attr='location')
    location = indexes.LocationField(model_attr="get_location")
    created = indexes.DateTimeField(model_attr="created")

    def get_model(self):
        return Checkin

    def prepare_text(self, obj):
        # Because I don't feel like creating a template just for this.
        return "\n".join([obj.comment, obj.username])
