from haystack import indexes
from core.models import MockModel


class SimpleMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')
    score = indexes.CharField(model_attr='score')

    def get_model(self):
        return MockModel
