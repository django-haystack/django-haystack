#!/usr/bin/env python
import os
import sys

import django
from django.core.management import call_command


def run_all(argv=None):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    os.environ["DJANGO_SETTINGS_MODULE"] = "test_haystack.settings"
    django.setup()

    call_command("test", sys.argv[1:])


if __name__ == "__main__":
    run_all(sys.argv)
