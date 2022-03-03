#!/usr/bin/env python
from setuptools import setup

install_requires = ["Django>=2.2"]

tests_require = [
    "pysolr>=3.7.0",
    "whoosh>=2.5.4,<3.0",
    "python-dateutil",
    "geopy==2.0.0",
    "nose",
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
    project_urls={
        "Documentation": "https://django-haystack.readthedocs.io",
        "Source": "https://github.com/django-haystack/django-haystack",
    },
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
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "elasticsearch": ["elasticsearch>=5,<8"],
    },
    test_suite="test_haystack.run_tests.run_all",
)
