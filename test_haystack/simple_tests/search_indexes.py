from haystack import indexes
from ..core.models import MockModel, ScoreMockModel


class SimpleMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return MockModel

class SimpleMockScoreIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    score = indexes.CharField(model_attr='score')

    def get_model(self):
        return ScoreMockModel
