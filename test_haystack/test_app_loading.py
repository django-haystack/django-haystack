from types import GeneratorType, ModuleType

from django.test import TestCase
from django.urls import reverse

from haystack.utils import app_loading


class AppLoadingTests(TestCase):
    def test_load_apps(self):
        apps = app_loading.haystack_load_apps()
        self.assertIsInstance(apps, (list, GeneratorType))

        self.assertIn("hierarchal_app_django", apps)

        self.assertNotIn(
            "test_app_without_models",
            apps,
            msg="haystack_load_apps should exclude apps without defined models",
        )

    def test_get_app_modules(self):
        app_modules = app_loading.haystack_get_app_modules()
        self.assertIsInstance(app_modules, (list, GeneratorType))

        for i in app_modules:
            self.assertIsInstance(i, ModuleType)

    def test_get_models_all(self):
        models = app_loading.haystack_get_models("core")
        self.assertIsInstance(models, (list, GeneratorType))

    def test_get_models_specific(self):
        from test_haystack.core.models import MockModel

        models = app_loading.haystack_get_models("core.MockModel")
        self.assertIsInstance(models, (list, GeneratorType))
        self.assertListEqual(models, [MockModel])

    def test_hierarchal_app_get_models(self):
        models = app_loading.haystack_get_models("hierarchal_app_django")
        self.assertIsInstance(models, (list, GeneratorType))
        self.assertSetEqual(
            set(str(i._meta) for i in models),
            set(
                (
                    "hierarchal_app_django.hierarchalappsecondmodel",
                    "hierarchal_app_django.hierarchalappmodel",
                )
            ),
        )

    def test_hierarchal_app_specific_model(self):
        models = app_loading.haystack_get_models(
            "hierarchal_app_django.HierarchalAppModel"
        )
        self.assertIsInstance(models, (list, GeneratorType))
        self.assertSetEqual(
            set(str(i._meta) for i in models),
            set(("hierarchal_app_django.hierarchalappmodel",)),
        )


class AppWithoutModelsTests(TestCase):
    # Confirm that everything works if an app is enabled

    def test_simple_view(self):
        url = reverse("app-without-models:simple-view")
        resp = self.client.get(url)
        self.assertEqual(resp.content.decode("utf-8"), "OK")
