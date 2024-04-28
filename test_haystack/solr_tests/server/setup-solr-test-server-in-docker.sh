# figure out the solr container ID
SOLR_CONTAINER=`docker ps -f ancestor=solr:6 --format '{{.ID}}'`

# set up a solr core
docker exec $SOLR_CONTAINER ./bin/solr create -c collection1 -p 8983 -n basic_config
# copy the testing schema to the collection and fix permissions
docker cp ./test_haystack/solr_tests/server/confdir/solrconfig.xml $SOLR_CONTAINER:/opt/solr/server/solr/collection1/conf/solrconfig.xml
docker cp ./test_haystack/solr_tests/server/confdir/schema.xml $SOLR_CONTAINER:/opt/solr/server/solr/collection1/conf/schema.xml
docker exec $SOLR_CONTAINER mv /opt/solr/server/solr/collection1/conf/managed-schema /opt/solr/server/solr/collection1/conf/managed-schema.old
docker exec -u root $SOLR_CONTAINER chown -R solr:solr /opt/solr/server/solr/collection1
# reload the solr core
curl "http://localhost:9001/solr/admin/cores?action=RELOAD&core=collection1"
