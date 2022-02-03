.. _ref-running-tests:

=============
Running Tests
=============

Everything
==========

The simplest way to get up and running with Haystack's tests is to run::

    python setup.py test

This installs all of the backend libraries & all dependencies for getting the
tests going and runs the tests. You will still have to setup search servers
(for running Solr tests, the spatial Solr tests & the Elasticsearch tests).


Cherry-Picked
=============

If you'd rather not run all the tests, run only the backends you need since
tests for backends that are not running will be skipped.

``Haystack`` is maintained with all tests passing at all times, so if you
receive any errors during testing, please check your setup and file a report if
the errors persist.

To run just a portion of the tests you can use the script ``run_tests.py`` and
just specify the files or directories you wish to run, for example::

    cd test_haystack
    ./run_tests.py whoosh_tests test_loading.py

The ``run_tests.py`` script is just a tiny wrapper around the nose_ library and
any options you pass to it will be passed on; including ``--help`` to get a
list of possible options::

    cd test_haystack
    ./run_tests.py --help

.. _nose: https://nose.readthedocs.io/en/latest/

Configuring Solr
================

Haystack assumes that you have a Solr server running on port ``9001`` which
uses the schema and configuration provided in the
``test_haystack/solr_tests/server/`` directory. For convenience, a script is
provided which will download, configure and start a test Solr server::

    test_haystack/solr_tests/server/start-solr-test-server.sh

If no server is found all solr-related tests will be skipped.

Configuring Elasticsearch
=========================

The test suite will try to connect to Elasticsearch on port ``9200``. If no
server is found all elasticsearch tests will be skipped. Note that the tests
are destructive - during the teardown phase they will wipe the cluster clean so
make sure you don't run them against an instance with data you wish to keep.

If you want to run the geo-django tests you may need to review the
`GeoDjango GEOS and GDAL settings`_ before running these commands::

	cd test_haystack
	./run_tests.py elasticsearch_tests

.. _GeoDjango GEOS and GDAL settings: https://docs.djangoproject.com/en/1.7/ref/contrib/gis/install/geolibs/#geos-library-path
