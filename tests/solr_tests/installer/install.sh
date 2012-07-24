DIR="$( cd "$( dirname "$0" )" && pwd )"

mkdir /usr/share/solr /var/log/solr
mv apache-solr-3.6.1/* /usr/share/solr
cp $DIR/init.sh /etc/init.d/jetty
chmod 755 /etc/init.d/jetty
cp $DIR/default.sh /etc/default/jetty
cp $DIR/logging.xml /usr/share/solr/example/etc/jetty-logging.xml
useradd -d /usr/share/solr -s /bin/false solr
chown solr:solr -R /usr/share/solr
chown solr:solr -R /var/log/solr
cp $DIR/schema.xml /usr/share/solr/example/solr/conf/schema.xml
