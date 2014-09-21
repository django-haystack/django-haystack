# encoding: utf-8
from __future__ import absolute_import, print_function, unicode_literals

from types import GeneratorType

from django.core.urlresolvers import reverse
from django.test import TestCase

from haystack.utils import app_loading


class AppLoadingTests(TestCase):
    def test_load_apps(self):
        apps = app_loading.load_apps()
        self.assertIsInstance(apps, (list, GeneratorType))

    def test_get_models_all(self):
        models = app_loading.get_models('core')
        self.assertIsInstance(models, (list, GeneratorType))

    def test_get_models_specific(self):
        from test_haystack.core.models import MockModel

        models = app_loading.get_models('core.MockModel')
        self.assertIsInstance(models, (list, GeneratorType))
        self.assertListEqual(models, [MockModel])


class AppWithoutModelsTests(TestCase):
    # Confirm that everything works if an app is enabled

    def test_simple_view(self):
        url = reverse('app-without-models:simple-view')
        resp = self.client.get(url)
        self.assertEqual(resp.content.decode('utf-8'), 'OK')
