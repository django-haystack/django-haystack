#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='django-haystack',
    version='1.0.0b',
    description='Pluggable search for Django.',
    author='Daniel Lindsley',
    author_email='daniel@toastdriven.com',
    url='http://haystacksearch.org/',
    package_dir={'haystack': 'haystack'},
    packages=['haystack', 'haystack.backends', 'haystack.management', 'haystack.management.commands'],
    package_data={'haystack': ['templates/*']},
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Web Environment',
                 'Framework :: Django',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: MIT License',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Utilities'],
)