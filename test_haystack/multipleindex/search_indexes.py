from haystack import indexes
from .models import Foo, Bar


# To test additional ignores...
class BaseIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='body')

    def get_model(self):
        return Foo


class FooIndex(BaseIndex, indexes.Indexable):
    def index_queryset(self, using=None):
        qs = super(FooIndex, self).index_queryset(using=using)
        if using == "filtered_whoosh":
            qs = qs.filter(body__contains="1")
        return qs


# Import the old way & make sure things don't explode.
from haystack.indexes import SearchIndex, Indexable


class BarIndex(SearchIndex, Indexable):
    text = indexes.CharField(document=True)

    def get_model(self):
        return Bar

    def prepare_text(self, obj):
        return u"%s\n%s" % (obj.author, obj.content)
