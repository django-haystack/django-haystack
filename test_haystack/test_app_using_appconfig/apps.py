from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig


class SimpleTestAppConfig(AppConfig):
    name = 'test_haystack.test_app_using_appconfig'
    verbose_name = "Simple test app using AppConfig"
