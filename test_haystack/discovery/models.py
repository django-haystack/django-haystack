# encoding: utf-8
from django.db import models


class Foo(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return self.title


class Bar(models.Model):
    author = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return self.author
