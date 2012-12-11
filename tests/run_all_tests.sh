#!/bin/bash

set -e

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

export FAIL=0

echo "** CORE **"
$TEST_RUNNER test core --settings=settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** DISCOVERY **"
$TEST_RUNNER test discovery --settings=discovery_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** OVERRIDES **"
$TEST_RUNNER test overrides --settings=overrides_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** SIMPLE **"
$TEST_RUNNER test simple_tests --settings=simple_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** SOLR **"
$TEST_RUNNER test solr_tests --settings=solr_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** Elasticsearch **"
$TEST_RUNNER test elasticsearch_tests --settings=elasticsearch_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** WHOOSH **"
$TEST_RUNNER test whoosh_tests --settings=whoosh_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** MULTIPLE INDEX **"
$TEST_RUNNER test multipleindex --settings=multipleindex_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

echo "** SPATIAL **"
$TEST_RUNNER test spatial --settings=spatial_settings $TEST_RUNNER_ARGS || FAIL=1
echo ""

exit $FAIL