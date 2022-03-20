""""""
import unittest

import django
from django.test import TestCase

import haystack


class AppConfigCompatibilityTestCase(TestCase):
    @unittest.skipIf(
        django.VERSION >= (3, 2), "default_app_config is deprecated since django 3.2."
    )
    def testDefaultAppConfigIsDefined_whenDjangoVersionIsLessThan3_2(self):
        has_default_appconfig_attr = hasattr(haystack, "default_app_config")
        self.assertTrue(has_default_appconfig_attr)

    @unittest.skipIf(
        django.VERSION < (3, 2),
        "default_app_config should be used in versions prior to django 3.2.",
    )
    def testDefaultAppConfigIsDefined_whenDjangoVersionIsMoreThan3_2(self):
        has_default_appconfig_attr = hasattr(haystack, "default_app_config")
        self.assertFalse(has_default_appconfig_attr)
