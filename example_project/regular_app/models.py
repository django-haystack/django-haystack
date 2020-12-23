# encoding: utf-8
import datetime

from django.db import models

BREED_CHOICES = [
    ("collie", "Collie"),
    ("labrador", "Labrador"),
    ("pembroke", "Pembroke Corgi"),
    ("shetland", "Shetland Sheepdog"),
    ("border", "Border Collie"),
]


class Dog(models.Model):
    breed = models.CharField(max_length=255, choices=BREED_CHOICES)
    name = models.CharField(max_length=255)
    owner_last_name = models.CharField(max_length=255, blank=True)
    birth_date = models.DateField(default=datetime.date.today)
    bio = models.TextField(blank=True)
    public = models.BooleanField(default=True)
    created = models.DateTimeField(default=datetime.datetime.now)
    updated = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return self.full_name()

    @models.permalink
    def get_absolute_url(self):
        return ("dog_detail", [], {"id": self.id})

    def full_name(self):
        if self.owner_last_name:
            return "%s %s" % (self.name, self.owner_last_name)

        return self.name


class Toy(models.Model):
    dog = models.ForeignKey(Dog, related_name="toys")
    name = models.CharField(max_length=60)

    def __str__(self):
        return "%s's %s" % (self.dog.name, self.name)
