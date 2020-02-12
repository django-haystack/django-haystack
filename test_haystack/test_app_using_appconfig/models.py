# encoding: utf-8
from django.db.models import CharField, Model


class MicroBlogPost(Model):
    text = CharField(max_length=140)
