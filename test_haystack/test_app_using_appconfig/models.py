# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models import CharField, Model


class MicroBlogPost(Model):
    text = CharField(max_length=140)
