#!/usr/bin/env python
# encoding: utf-8
import sys
from os.path import abspath, dirname

import nose


def run_all(argv=None):
    sys.exitfunc = lambda: sys.stderr.write("Shutting down....\n")

    # always insert coverage when running tests through setup.py
    if argv is None:
        argv = [
            "nosetests",
            "--with-coverage",
            "--cover-package=haystack",
            "--cover-erase",
            "--verbose",
        ]

    nose.run_exit(argv=argv, defaultTest=abspath(dirname(__file__)))


if __name__ == "__main__":
    run_all(sys.argv)
