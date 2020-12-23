# encoding: utf-8
import datetime

from django.db import models


class Cat(models.Model):
    name = models.CharField(max_length=255)
    birth_date = models.DateField(default=datetime.date.today)
    bio = models.TextField(blank=True)
    created = models.DateTimeField(default=datetime.datetime.now)
    updated = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ("cat_detail", [], {"id": self.id})
