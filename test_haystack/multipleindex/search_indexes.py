from haystack import indexes
from haystack.indexes import Indexable, SearchIndex

from .models import Bar, Foo


# To test additional ignores...
class BaseIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr="body")

    def get_model(self):
        return Foo


# Import the old way & make sure things don't explode.


class BarIndex(SearchIndex, Indexable):
    text = indexes.CharField(document=True)

    def get_model(self):
        return Bar

    def prepare_text(self, obj):
        return "%s\n%s" % (obj.author, obj.content)
