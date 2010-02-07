from haystack.indexes import *
from haystack import site
from regular_app.models import Dog


# More typical usage involves creating a subclassed `SearchIndex`. This will
# provide more control over how data is indexed, generally resulting in better
# search.
class DogIndex(RealTimeSearchIndex):
    text = CharField(document=True, use_template=True)
    # We can pull data straight out of the model via `model_attr`.
    breed = CharField(model_attr='breed')
    # Note that callables are also OK to use.
    name = CharField(model_attr='full_name')
    bio = CharField(model_attr='name')
    birth_date = DateField(model_attr='birth_date')
    # Note that we can't assign an attribute here. We'll manually prepare it instead.
    toys = MultiValueField()
    
    def get_queryset(self):
        return Dog.objects.filter(public=True)
    
    def prepare_toys(self, obj):
        # Store a list of id's for filtering
        return [toy.id for toy in obj.toys.all()]
        
        # Alternatively, you could store the names if searching for toy names
        # is more useful.
        # return [toy.name for toy in obj.toys.all()]


site.register(Dog, DogIndex)
