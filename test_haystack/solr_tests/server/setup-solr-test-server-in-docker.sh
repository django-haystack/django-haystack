# figure out the solr container ID
SOLR_CONTAINER=`docker ps -f ancestor=solr:6 --format '{{.ID}}'`

LOCAL_CONFDIR=./test_haystack/solr_tests/server/confdir
CONTAINER_CONFDIR=/opt/solr/server/solr/collection1/conf

# set up a solr core
docker exec $SOLR_CONTAINER ./bin/solr create -c collection1 -p 8983 -n basic_config
# copy the testing schema to the collection and fix permissions
docker cp $LOCAL_CONFDIR/solrconfig.xml $SOLR_CONTAINER:$CONTAINER_CONFDIR/solrconfig.xml
docker cp $LOCAL_CONFDIR/schema.xml $SOLR_CONTAINER:$CONTAINER_CONFDIR/schema.xml
docker exec $SOLR_CONTAINER mv $CONTAINER_CONFDIR/managed-schema $CONTAINER_CONFDIR/managed-schema.old
docker exec -u root $SOLR_CONTAINER chown -R solr:solr /opt/solr/server/solr/collection1
# reload the solr core
curl "http://localhost:9001/solr/admin/cores?action=RELOAD&core=collection1"
