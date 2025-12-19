#!/usr/bin/env python
import multiprocessing
import os
import sys

import django
from django.core.management import call_command


def run_all(argv=None):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    os.environ["DJANGO_SETTINGS_MODULE"] = "test_haystack.settings"
    django.setup()

    # Python >= 3.14: default start method changed from `fork` --> `forkserver`
    # (No state inheritance in child processes)
    # https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
    if sys.version_info >= (3, 14):
        multiprocessing.set_start_method("fork", force=True)
    call_command("test", sys.argv[1:])


if __name__ == "__main__":
    run_all(sys.argv)
