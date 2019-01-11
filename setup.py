#!/usr/bin/env python
# encoding: utf-8

# n.b. we can't have unicode_literals here due to http://bugs.python.org/setuptools/issue152
from __future__ import absolute_import, division, print_function

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools

    use_setuptools()
    from setuptools import setup

install_requires = ["Django>=1.11"]

tests_require = [
    "pysolr>=3.7.0",
    "whoosh>=2.5.4,<3.0",
    "python-dateutil",
    "geopy==0.95.1",
    "nose",
    "mock",
    "coverage",
    "requests",
]

setup(
    name="django-haystack",
    use_scm_version=True,
    description="Pluggable search for Django.",
    author="Daniel Lindsley",
    author_email="daniel@toastdriven.com",
    long_description=open("README.rst", "r").read(),
    url="http://haystacksearch.org/",
    packages=[
        "haystack",
        "haystack.backends",
        "haystack.management",
        "haystack.management.commands",
        "haystack.templatetags",
        "haystack.utils",
    ],
    package_data={
        "haystack": ["templates/panels/*", "templates/search_configuration/*"]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.0",
        "Framework :: Django :: 2.1",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="test_haystack.run_tests.run_all",
    setup_requires=["setuptools_scm"],
)
