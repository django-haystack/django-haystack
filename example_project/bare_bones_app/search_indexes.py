from haystack import indexes
from bare_bones_app.models import Cat


# For the most basic usage, you can use a subclass of
# `haystack.indexes.BasicSearchIndex`, whose only requirement will be that
# you create a `search/indexes/bare_bones_app/cat_text.txt` data template
# for indexing.
class CatIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def get_model(self):
        return Cat
