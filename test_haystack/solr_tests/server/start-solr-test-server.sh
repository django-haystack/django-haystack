#!/bin/bash

set -e

SOLR_VERSION=6.6.4
SOLR_DIR=solr


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

echo "Extracting Solr ${SOLR_ARCHIVE} to ${TEST_ROOT}/${SOLR_DIR}"
rm -rf ${SOLR_DIR}
mkdir ${SOLR_DIR}
FULL_SOLR_DIR=$(readlink -f ./${SOLR_DIR})
tar -C ${SOLR_DIR} -xf ${SOLR_ARCHIVE} --strip-components=1

# These tuning options will break on Java 10 and for testing we don't care about
# production server optimizations:
export GC_LOG_OPTS=""
export GC_TUNE=""

export SOLR_LOGS_DIR="${FULL_SOLR_DIR}/logs"

install -d ${SOLR_LOGS_DIR}

echo "Changing into ${FULL_SOLR_DIR} "

cd ${FULL_SOLR_DIR}

echo "Creating Solr Core"
./bin/solr start -p ${SOLR_PORT}
./bin/solr create -c collection1 -p ${SOLR_PORT} -n basic_config
./bin/solr create -c mgmnt -p ${SOLR_PORT}

echo "Solr system information:"
curl --fail --silent 'http://localhost:9001/solr/admin/info/system?wt=json&indent=on' | python -m json.tool
./bin/solr stop -p ${SOLR_PORT}

CONF_DIR=${TEST_ROOT}/confdir
CORE_DIR=${FULL_SOLR_DIR}/server/solr/collection1
mv ${CORE_DIR}/conf/managed-schema ${CORE_DIR}/conf/managed-schema.old
cp ${CONF_DIR}/* ${CORE_DIR}/conf/

echo 'Starting server'
cd server
# We use exec to allow process monitors to correctly kill the
# actual Java process rather than this launcher script:
export CMD="java -Djetty.port=${SOLR_PORT} -Djava.awt.headless=true -Dapple.awt.UIElement=true -jar start.jar --module=http -Dsolr.install.dir=${FULL_SOLR_DIR} -Dsolr.log.dir=${SOLR_LOGS_DIR}"

if [ -z "${BACKGROUND_SOLR}" ]; then
    exec $CMD
else
    exec $CMD >/dev/null &
fi
