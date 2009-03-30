=============
Running Tests
=============

In order to test Haystack with the minimum amount of unnecessary mocking and to
stay as close to real-world use as possible, ``Haystack`` ships with a test
app (called ``core``) within the ``django-haystack/tests`` directory.

In the event you need to run ``Haystack``'s tests (such as developing a backend
or testing bugfixes/modifications), here are the steps to getting them running::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`
    export DJANGO_SETTINGS_MODULE=settings
    django-admin.py test core

``Haystack`` is maintained with all tests passing at all times, so if you
receive any errors during testing, please check your setup and file a report if
the errors persist.
