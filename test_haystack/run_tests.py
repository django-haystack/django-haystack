#!/usr/bin/env python
from __future__ import print_function

import sys
from os.path import dirname, abspath

import nose

def run_all(argv=None):
    sys.exitfunc = lambda: sys.stderr.write('Shutting down....\n')

    # always insert coverage when running tests through setup.py
    if argv is None:
        argv = [
            'nosetests', '--with-coverage', '--cover-package=haystack',
            '--cover-erase', '--verbose',
        ]

    nose.run_exit(
        argv=argv,
        defaultTest=abspath(dirname(__file__))
    )

if __name__ == '__main__':
    run_all(sys.argv)


