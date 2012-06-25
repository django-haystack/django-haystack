.PHONY: core test

solr:
	curl `curl -q -s -S -L http://www.apache.org/dyn/closer.cgi?path=lucene/solr/3.6.0/apache-solr-3.6.0.tgz | sed -n '/^<p><a href="http/s/.*"\\(.*\\)".*/\\1/gp'` | tar xzf -
	sudo mkdir /usr/share/solr /var/log/solr
	sudo mv apache-solr-3.6.0 /usr/share/solr
	sudo cp solr_tests/jetty-init.sh /etc/init.d/jetty
	sudo chmod 755 /etc/init.d/jetty
	sudo cp solr_tests/jetty-default.sh /etc/default/jetty
	sudo cp solr_tests/jetty-logging.xml /usr/share/solr/example/etc/jetty-logging.xml
	sudo useradd -d /usr/share/solr -s /bin/false solr
	sudo chown solr:solr -R /usr/share/solr
	sudo chown solr:solr -R /var/log/solr
	sudo cp solr_tests/solr_test_schema.xml /usr/share/solr/example/solr/conf/schema.xml

core:
	django-admin.py test core --settings=core.settings

simple:
	django-admin.py test simple --settings=simple.settings


test: core simple
