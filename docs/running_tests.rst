=============
Running Tests
=============

Core Haystack Functionality
===========================

In order to test Haystack with the minimum amount of unnecessary mocking and to
stay as close to real-world use as possible, ``Haystack`` ships with a test
app (called ``core``) within the ``django-haystack/tests`` directory.

In the event you need to run ``Haystack``'s tests (such as testing 
bugfixes/modifications), here are the steps to getting them running::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`
    export DJANGO_SETTINGS_MODULE=settings
    django-admin.py test core

``Haystack`` is maintained with all tests passing at all times, so if you
receive any errors during testing, please check your setup and file a report if
the errors persist.


Backends
========

If you want to test a backend, the steps are the same with the exception of
the settings module. To test each engine, use the ``engine_settings`` module
within the ``tests`` directory, substituting the ``engine`` for the name of the
proper backend. For instance, to run the Solr backend's tests::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`
    export DJANGO_SETTINGS_MODULE=solr_settings
    django-admin.py test core
