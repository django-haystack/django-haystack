import datetime
from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField(blank=True)
    longitude = models.FloatField(blank=True)
    
    def __unicode__(self):
        return self.name
