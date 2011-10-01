from haystack import indexes
from spatial_app.models import Restaurant

class RestaurantIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    geocode = indexes.LocationField()
    
    def get_model(self):
        return Restaurant
    
    def index_queryset(self):
        return self.get_model().objects.all()
    
