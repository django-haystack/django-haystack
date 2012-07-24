export PYTHONPATH = .:$$PYTHONPATH
RUNTEST = django-admin.py test

.PHONY: test

core:
	DJANGO_SETTINGS_MODULE=core.settings $(RUNTEST) core

simple:
	DJANGO_SETTINGS_MODULE=simple.settings $(RUNTEST) simple

discovery:
	DJANGO_SETTINGS_MODULE=discovery.settings $(RUNTEST) discovery

overrides:
	DJANGO_SETTINGS_MODULE=overrides.settings $(RUNTEST) overrides

solr:
	curl `curl -q -s -S -L http://www.apache.org/dyn/closer.cgi?path=lucene/solr/3.6.1/apache-solr-3.6.1.tgz | sed -n '/^<p><a href="http/s/.*"\\(.*\\)".*/\\1/gp'` | tar xzf -
	sudo solr_tests/installer/install.sh
	DJANGO_SETTINGS_MODULE=solr.settings $(RUNTEST) solr

whoosh:
	DJANGO_SETTINGS_MODULE=whoosh_tests.settings $(RUNTEST) whoosh_tests

multipleindex:
	DJANGO_SETTINGS_MODULE=multipleindex.settings $(RUNTEST) multipleindex

spatial:
	DJANGO_SETTINGS_MODULE=spatial.settings $(RUNTEST) spatial

test: core simple discovery overrides solr whoosh multipleindex spatial
