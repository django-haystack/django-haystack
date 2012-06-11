SHELL = /bin/bash
DJANGOADMIN = $(shell which django-admin.py)
TESTRUNNER = $(DJANGOADMIN) test
TEST = PYTHONPATH=./tests:$(PYTHONPATH) $(TESTRUNNER)

define JETTY_DEFAULT
JAVA_HOME=/usr/java/default
JAVA_OPTIONS="-Dsolr.solr.home=/usr/share/solr/example/solr \$JAVA_OPTIONS"
JETTY_HOME=/usr/share/solr/example
JETTY_USER=solr
JETTY_LOGS=/var/log/solr
JAVA_HOME=/usr/lib/jvm/default-java
JDK_DIRS="/usr/lib/jvm/default-java /usr/lib/jvm/java-6-sun"
endef
export JETTY_DEFAULT

define JETTY_LOGGING

endef
export JETTY_LOGGING

all:
	# $(TEST) core
	sudo ls -la

two:
	python -c 'import sys; print sys.path'


test:
	cd tests
	PYTHONPATH=$(shell pwd)/tests:${PYTHONPATH}  core

install-solr:
	curl `curl -q -s -S -L http://www.apache.org/dyn/closer.cgi?path=lucene/solr/3.6.0/apache-solr-3.6.0.tgz | sed -n '/^<p><a href="http/s/.*"\\(.*\\)".*/\\1/gp'` | tar xzf -
	sudo mkdir /usr/share/solr
	sudo mv apache-solr-3.6.0 /usr/share/solr
	sudo curl http://svn.codehaus.org/jetty/jetty/branches/jetty-6.1/bin/jetty.sh > /etc/init.d/jetty
	sudo chmod 755 /etc/init.d/jetty
	sudo echo "$$JETTY_DEFAULT" > /etc/default/jetty
	sudo mkdir -p /var/log/solr
	sudo echo "$$JETTY_LOGGING" > /usr/share/solr/example/etc/jetty-logging.xml
	sudo useradd -d /usr/share/solr -s /bin/false solr
	sudo chown solr:solr -R /usr/share/solr
	sudo chown solr:solr -R /var/log/solr

xapian:
	sudo apt-get install libxapian22 python-xapian
