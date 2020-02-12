# encoding: utf-8
from django.db.models import BooleanField, CharField, Model


class HierarchalAppModel(Model):
    enabled = BooleanField(default=True)


class HierarchalAppSecondModel(Model):
    title = CharField(max_length=16)
