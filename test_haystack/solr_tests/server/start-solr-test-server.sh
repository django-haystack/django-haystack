#!/bin/bash

set -e

export TEST_ROOT=$(realpath $( dirname $0 ) )

if [ ! -f solr-4.6.0.tgz ]; then
    curl -O http://archive.apache.org/dist/lucene/solr/4.6.0/solr-4.6.0.tgz
fi

echo "Extracting Solr 4.6.0 to `pwd`/solr4/"
rm -rf solr4
mkdir solr4
tar -C solr4 -xf solr-4.6.0.tgz --strip-components 2 solr-4.6.0/example
tar -C solr4 -xf solr-4.6.0.tgz --strip-components 1 solr-4.6.0/dist solr-4.6.0/contrib

echo "Changing into solr4"

cd solr4

echo "Configuring Solr"

cp ${TEST_ROOT}/solrconfig.xml solr/collection1/conf/solrconfig.xml
cp ${TEST_ROOT}/schema.xml solr/collection1/conf/schema.xml

# Fix paths for the content extraction handler:
perl -p -i -e 's|<lib dir="../../../contrib/|<lib dir="../../contrib/|'g solr/*/conf/solrconfig.xml
perl -p -i -e 's|<lib dir="../../../dist/|<lib dir="../../dist/|'g solr/*/conf/solrconfig.xml

# Add MoreLikeThis handler
perl -p -i -e 's|<!-- A Robust Example|<!-- More like this request handler -->\n  <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />\n\n\n  <!-- A Robust Example|'g solr/*/conf/solrconfig.xml

echo 'Starting server'
# We use exec to allow process monitors to correctly kill the
# actual Java process rather than this launcher script:
exec java -D9001 -Djava.awt.headless=true -Dapple.awt.UIElement=true -jar start.jar
