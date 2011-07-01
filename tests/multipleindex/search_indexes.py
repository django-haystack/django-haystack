from haystack import indexes
from multipleindex.models import Foo, Bar


# To test additional ignores...
class BaseIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='body')
    
    def get_model(self):
        return Foo


class FooIndex(BaseIndex, indexes.Indexable):
    pass


# Import the old way & make sure things don't explode.
from haystack.indexes import SearchIndex, RealTimeSearchIndex


class BarIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    
    def get_model(self):
        return Bar
    
    def prepare_text(self, obj):
        return u"%s\n%s" % (obj.author, obj.content)
