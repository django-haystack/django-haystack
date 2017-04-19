# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models import BooleanField, CharField, Model


class HierarchalAppModel(Model):
    enabled = BooleanField(default=True)


class HierarchalAppSecondModel(Model):
    title = CharField(max_length=16)
