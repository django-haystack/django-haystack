""""""

import unittest

import django
from django.test import TestCase

import haystack


class AppConfigCompatibilityTestCase(TestCase):

    def testDefaultAppConfigIsDefined_whenDjangoVersionIsMoreThan3_2(self):
        has_default_appconfig_attr = hasattr(haystack, "default_app_config")
        self.assertFalse(has_default_appconfig_attr)
