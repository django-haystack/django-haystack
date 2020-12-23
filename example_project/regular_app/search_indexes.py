# encoding: utf-8
from regular_app.models import Dog

from haystack import indexes


# More typical usage involves creating a subclassed `SearchIndex`. This will
# provide more control over how data is indexed, generally resulting in better
# search.
class DogIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    # We can pull data straight out of the model via `model_attr`.
    breed = indexes.CharField(model_attr="breed")
    # Note that callables are also OK to use.
    name = indexes.CharField(model_attr="full_name")
    bio = indexes.CharField(model_attr="name")
    birth_date = indexes.DateField(model_attr="birth_date")
    # Note that we can't assign an attribute here. We'll manually prepare it instead.
    toys = indexes.MultiValueField()

    def get_model(self):
        return Dog

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(public=True)

    def prepare_toys(self, obj):
        # Store a list of id's for filtering
        return [toy.id for toy in obj.toys.all()]

        # Alternatively, you could store the names if searching for toy names
        # is more useful.
        # return [toy.name for toy in obj.toys.all()]
