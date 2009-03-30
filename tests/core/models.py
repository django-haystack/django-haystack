# A couple models for Haystack to test with.
import datetime
from django.db import models


class MockModel(models.Model):
    user = models.CharField(max_length=255)
    foo = models.CharField(max_length=255, blank=True)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.user


class AnotherMockModel(models.Model):
    user = models.CharField(max_length=255)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.user
