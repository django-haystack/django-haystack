#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

install_requires = [
    'Django',
]

tests_require = [
    'elasticsearch',
    'pysolr>=3.2.0',
    'whoosh==2.5.4',
    'lxml==3.2.3',
    'python-dateutil',
    'geopy==0.95.1',
    'httplib2==0.8',

    'nose',
    'mock',
    'coverage',
]

setup(
    name='django-haystack',
    version='2.3.1',
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
        'haystack': [
            'templates/panels/*',
            'templates/search_configuration/*',
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="test_haystack.run_tests.run_all",
)
