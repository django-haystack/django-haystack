#!/bin/bash

if [ "$1" == "--help" ]; then
    echo "Runs the test suite for all backends"
    echo
    echo "See docs/running_tests.rst for instructions on installing test"
    echo "search engine instances"
    echo
    echo "Use $0 --with-coverage to execute tests using coverage.py"
    echo
    exit 0
elif [ "$1" == "--with-coverage" ]; then
    TEST_RUNNER="coverage run --source=$(realpath "$(dirname "$0")/../haystack") -- `which django-admin.py`"
else
    TEST_RUNNER=django-admin.py
fi

echo "** CORE **"
$TEST_RUNNER test core --settings=settings
echo ""

echo "** DISCOVERY **"
$TEST_RUNNER test discovery --settings=discovery_settings
echo ""

echo "** OVERRIDES **"
$TEST_RUNNER test overrides --settings=overrides_settings
echo ""

echo "** SIMPLE **"
$TEST_RUNNER test simple_tests --settings=simple_settings
echo ""

echo "** SOLR **"
$TEST_RUNNER test solr_tests --settings=solr_settings
echo ""

echo "** Elasticsearch **"
$TEST_RUNNER test elasticsearch_tests --settings=elasticsearch_settings
echo ""

echo "** WHOOSH **"
$TEST_RUNNER test whoosh_tests --settings=whoosh_settings
echo ""

echo "** MULTIPLE INDEX **"
$TEST_RUNNER test multipleindex --settings=multipleindex_settings
echo ""

echo "** SPATIAL **"
$TEST_RUNNER test spatial --settings=spatial_settings
echo ""
