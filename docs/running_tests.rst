.. _ref-running-tests:

=============
Running Tests
=============

Dependencies
============

Everything
----------

The simplest way to get up and running with Haystack's tests is to run::

    pip install -r tests/requirements.txt

This installs all of the backend libraries & all dependencies for getting the
tests going. You will still have to setup search servers (for running Solr
tests, the spatial Solr tests & the Elasticsearch tests).


Cherry-Picked
-------------

If you'd rather not run all the tests, install only the backends you need.
Additionally, ``Haystack`` uses the Mock_ library for testing. You will need
to install it before running the tests::

    pip install mock

.. _Mock: http://pypi.python.org/pypi/mock


Core Haystack Functionality
===========================

In order to test Haystack with the minimum amount of unnecessary mocking and to
stay as close to real-world use as possible, ``Haystack`` ships with a test
app (called ``core``) within the ``django-haystack/tests`` directory.

In the event you need to run ``Haystack``'s tests (such as testing
bugfixes/modifications), here are the steps to getting them running::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`/..:`pwd`
    django-admin.py test core --settings=settings

``Haystack`` is maintained with all tests passing at all times, so if you
receive any errors during testing, please check your setup and file a report if
the errors persist.

Backends
========

If you want to test a backend, the steps are the same with the exception of
the settings module and the app to test. To test an engine, use the
``engine_settings`` module within the ``tests`` directory, substituting the
``engine`` for the name of the proper backend. You'll also need to specify the
app for that engine. For instance, to run the Solr backend's tests::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`/..:`pwd`
    django-admin.py test solr_tests --settings=solr_settings

Or, to run the Whoosh backend's tests::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`/..:`pwd`
    django-admin.py test whoosh_tests --settings=whoosh_settings

Or, to run the Elasticsearch backend's tests::

    cd django-haystack/tests
    export PYTHONPATH=`pwd`/..:`pwd`
    django-admin.py test elasticsearch_tests --settings=elasticsearch_settings

Configuring Solr
----------------

Haystack assumes that you have a Solr server running on port ``9001`` which uses the schema and
configuration provided in the ``tests/`` directory. Currently, these steps will result in a working
test server:

#. Download the current Solr release from http://lucene.apache.org/solr/
#. Copy ``tests/solrconfig.xml`` to ``example/solr/conf/solrconfig.xml``
#. Copy ``tests/solr_test_schema.xml`` to ``example/solr/conf/schema.xml``
#. Change into the ``example`` directory
#. Start Solr: ``java -Djetty.port=9001 -jar start.jar``