# encoding: utf-8
from __future__ import absolute_import

import os

test_runner = None
old_config = None

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_haystack.settings'


import django
if hasattr(django, 'setup'):
    django.setup()


def setup():
    global test_runner
    global old_config

    from django.test.simple import DjangoTestSuiteRunner
    test_runner = DjangoTestSuiteRunner()
    test_runner.setup_test_environment()
    old_config = test_runner.setup_databases()


def teardown():
    test_runner.teardown_databases(old_config)
    test_runner.teardown_test_environment()


