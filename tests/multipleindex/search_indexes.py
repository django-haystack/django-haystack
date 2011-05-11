from haystack import indexes
from multipleindex.models import Foo, Bar


class FooIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='body')
    
    def get_model(self):
        return Foo


class BarIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    
    def get_model(self):
        return Bar
    
    def prepare_text(self, obj):
        return u"%s\n%s" % (obj.author, obj.content)
