# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase

from .models import MicroBlogPost


class AppConfigTests(TestCase):
    def test_index_collection(self):
        from haystack import connections

        unified_index = connections['default'].get_unified_index()
        models = unified_index.get_indexed_models()

        self.assertIn(MicroBlogPost, models)
