import datetime

from django.db import models
from django.urls import reverse


class Cat(models.Model):
    name = models.CharField(max_length=255)
    birth_date = models.DateField(default=datetime.date.today)
    bio = models.TextField(blank=True)
    created = models.DateTimeField(default=datetime.datetime.now)
    updated = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("cat_detail", kwargs={"id": self.id})
