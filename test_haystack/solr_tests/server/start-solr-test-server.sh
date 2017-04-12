#!/bin/bash

set -e

SOLR_VERSION=6.4.0
SOLR_DIR=solr-${SOLR_VERSION}

SOLR_PORT=9001

cd $(dirname $0)

export TEST_ROOT=$(pwd)

export SOLR_ARCHIVE="${SOLR_VERSION}.tgz"

if [ -d "${HOME}/download-cache/" ]; then
    export SOLR_ARCHIVE="${HOME}/download-cache/${SOLR_ARCHIVE}"
fi

if [ -f ${SOLR_ARCHIVE} ]; then
    # If the tarball doesn't extract cleanly, remove it so it'll download again:
    tar -tf ${SOLR_ARCHIVE} > /dev/null || rm ${SOLR_ARCHIVE}
fi

if [ ! -f ${SOLR_ARCHIVE} ]; then
    SOLR_DOWNLOAD_URL=$(python get-solr-download-url.py $SOLR_VERSION)
    curl -Lo $SOLR_ARCHIVE ${SOLR_DOWNLOAD_URL} || (echo "Unable to download ${SOLR_DOWNLOAD_URL}"; exit 2)
fi

echo "Extracting Solr ${SOLR_ARCHIVE} to `pwd`/${SOLR_DIR}"
rm -rf solr-*
mkdir ${SOLR_DIR}
FULL_SOLR_DIR=$(readlink -f ./${SOLR_DIR})
tar -C ${SOLR_DIR} -xf ${SOLR_ARCHIVE} --strip-components=1

echo "Changing into ${SOLR_DIR} "

cd ${SOLR_DIR}

echo "Creating Solr Core"
GC_LOG_OPTS= ./bin/solr start -p ${SOLR_PORT}
GC_LOG_OPTS= ./bin/solr create -c collection1 -d ../confdir -p ${SOLR_PORT}
GC_LOG_OPTS= ./bin/solr stop -p ${SOLR_PORT}

# Add MoreLikeThis handler
#perl -p -i -e 's|<!-- A Robust Example|<!-- More like this request handler -->\n  <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />\n\n\n  <!-- A Robust Example|'g solr/*/conf/solrconfig.xml

echo 'Starting server'
cd server
# We use exec to allow process monitors to correctly kill the
# actual Java process rather than this launcher script:
export CMD="java -Djetty.port=${SOLR_PORT} -Djava.awt.headless=true -Dapple.awt.UIElement=true -jar start.jar --module=http -Dsolr.install.dir=${FULL_SOLR_DIR}"

if [ -z "${BACKGROUND_SOLR}" ]; then
    exec $CMD
else
    exec $CMD >/dev/null &
fi
