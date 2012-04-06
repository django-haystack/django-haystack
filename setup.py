#!/usr/bin/env python
# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='django-haystack',
    version='1.2.7',
    description='Pluggable search for Django.',
    author='Daniel Lindsley',
    author_email='daniel@toastdriven.com',
    long_description=open('README.rst', 'r').read(),
    url='http://haystacksearch.org/',
    packages=[
        'haystack',
        'haystack.backends',
        'haystack.management',
        'haystack.management.commands',
        'haystack.templatetags',
        'haystack.utils',
    ],
    package_data={
        'haystack': ['templates/search_configuration/*']
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities'
    ],
)
