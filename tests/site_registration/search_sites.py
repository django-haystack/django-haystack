from haystack import indexes
from haystack import site
from site_registration.models import Foo, Bar

class FooIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='body')

site.register(Foo, FooIndex)
site.register(Bar)
