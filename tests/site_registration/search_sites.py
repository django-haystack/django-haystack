from haystack.indexes import *
from haystack import site
from site_registration.models import Foo, Bar

class FooIndex(SearchIndex):
    text = CharField(document=True, model_attr='body')

site.register(Foo, FooIndex)
site.register(Bar)
