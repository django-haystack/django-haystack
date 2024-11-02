# Take a command line parameter or default to 9
SOLR_VERSION=${1:-9}
if [[ $SOLR_VERSION == 6 || $SOLR_VERSION == 7 ]]; then
    SOLR_DATA_DIR="/opt/solr/server/solr"
else
    SOLR_DATA_DIR="/var/solr/data"
fi
echo "Using Solr version: $SOLR_VERSION Data dir: $SOLR_DATA_DIR"
# figure out the solr container ID
SOLR_CONTAINER=`docker ps -f ancestor=solr:$SOLR_VERSION --format '{{.ID}}'`

LOCAL_CONFDIR=./test_haystack/solr_tests/server/confdir
# CONTAINER_CONFDIR=/var/solr/data/collection1/conf
CONTAINER_CONFDIR=$SOLR_DATA_DIR/collection1/conf

# check the solr version like: Solr version is: 9.6.1
docker exec $SOLR_CONTAINER ./bin/solr version

# set up a solr core
echo "0: Create Solr collection1"
docker exec $SOLR_CONTAINER ./bin/solr create -c collection1 -n basic_config
# copy the testing schema to the collection and fix permissions
echo "1: Copy schema.xml and solrconfig.xml"
docker cp $LOCAL_CONFDIR/solrconfig.xml $SOLR_CONTAINER:$CONTAINER_CONFDIR/solrconfig.xml
docker cp $LOCAL_CONFDIR/schema.xml $SOLR_CONTAINER:$CONTAINER_CONFDIR/schema.xml
echo "2: Move managed-schema to managed-schema.old and fixing permissions"
if [[ $SOLR_VERSION == 6 || $SOLR_VERSION == 7 || $SOLR_VERSION == 8 ]]; then
    docker exec $SOLR_CONTAINER mv $CONTAINER_CONFDIR/managed-schema $CONTAINER_CONFDIR/managed-schema.old
fi
docker exec -u root $SOLR_CONTAINER chown -R solr:solr $SOLR_DATA_DIR/collection1
echo "3: Reload Solr collection1"
# reload the solr core
curl "http://localhost:9001/solr/admin/cores?action=RELOAD&core=collection1"
