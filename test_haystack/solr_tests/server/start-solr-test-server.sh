#!/bin/bash

set -e

SOLR_VERSION=6.6.6

if [ -z "${BACKGROUND_SOLR}" ]; then
    ARGS=""
else
    ARGS="-d"
fi

# https://stackoverflow.com/a/246128/540644
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker run --rm ${ARGS} -p 9001:8983 \
    -v $DIR/solr-setup.sh:/solr-setup.sh \
    -v $DIR/confdir:/confdir:ro \
    --name haystack_solr solr:${SOLR_VERSION}-slim bash -c "/solr-setup.sh"
