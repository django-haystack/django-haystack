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

    python test_haystack/run_tests.py whoosh_tests test_loading.py

The ``run_tests.py`` script is just a tiny wrapper around the Django test
command and any options you pass to it will be passed on; including ``--help``
to get a list of possible options::

    python test_haystack/run_tests.py --help

Starting the search servers
===========================

A Compose file is provided which starts both Solr and Elasticsearch
preconfigured for the test suite::

    docker compose up -d

Both services declare health checks, so you can block until they are actually
ready to serve requests rather than merely started::

    docker compose up -d --wait

Shut the services down again when you are finished::

    docker compose down -v

The image versions can be overridden with environment variables:

``SOLR_VERSION``
    Tag of the ``solr`` image to run. Defaults to ``6``. This also selects
    which configuration directory is mounted into the container, so it must
    match a directory under ``solr/`` (for example ``SOLR_VERSION=6`` uses
    ``solr/6.x.x/conf/``).

``ELASTICSEARCH_VERSION``
    Tag of the ``docker.elastic.co/elasticsearch/elasticsearch`` image to run.
    Defaults to ``7.17.13``.

Configuring Solr
================

The ``solr`` service listens on port ``8983`` and creates a core named
``collection1``. On startup the container creates that core from Solr's
``basic_configs`` configset and then overwrites ``solrconfig.xml`` and
``schema.xml`` with the Haystack test configuration mounted from
``solr/<SOLR_VERSION>.x.x/conf/``, so the core is ready to index as soon as
the container reports healthy.

The test suite defaults to port ``8983``, so point it at the container by
exporting both Solr URLs before running the tests::

    export TEST_SOLR_URL="http://localhost:8983/solr/collection1"
    export TEST_SOLR_ADMIN_URL="http://localhost:8983/solr/admin/cores"

    python test_haystack/run_tests.py solr_tests

If no server is found all solr-related tests will be skipped.

Configuring Elasticsearch
=========================

The ``elasticsearch`` service listens on port ``9200`` as a single-node
cluster, which is where the test suite looks by default; no extra
configuration is needed. To use an instance elsewhere, set
``TEST_ELASTICSEARCH_1_URL``. If no server is found all elasticsearch tests
will be skipped. Note that the tests are destructive - during the teardown
phase they will wipe the cluster clean so make sure you don't run them against
an instance with data you wish to keep.

If you want to run the geo-django tests you may need to review the
`GeoDjango GEOS and GDAL settings`_ before running these commands::

	cd test_haystack
	./run_tests.py elasticsearch_tests

.. _GeoDjango GEOS and GDAL settings: https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/geolibs/#geos-library-path
