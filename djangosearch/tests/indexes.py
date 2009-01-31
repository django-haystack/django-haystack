from django.test import TestCase
from djangosearch import indexes


class SampleModelIndex(indexes.ModelIndex):
    content = indexes.ContentField()
    author = indexes.CharField('user')
    pub_date = indexes.DateTimeField('pub_date')


class ModelIndexTestCase(TestCase):
    pass
