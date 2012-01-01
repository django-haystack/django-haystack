#!/bin/sh
echo "** CORE **"
django-admin.py test core --settings=settings
echo ""

echo "** DISCOVERY **"
django-admin.py test discovery --settings=discovery_settings
echo ""

echo "** OVERRIDES **"
django-admin.py test overrides --settings=overrides_settings
echo ""

echo "** SIMPLE **"
django-admin.py test simple_tests --settings=simple_settings
echo ""

echo "** SOLR **"
django-admin.py test solr_tests --settings=solr_settings
echo ""

echo "** Elasticsearch **"
django-admin.py test elasticsearch_tests --settings=elasticsearch_settings
echo ""

echo "** WHOOSH **"
django-admin.py test whoosh_tests --settings=whoosh_settings
echo ""

echo "** MULTIPLE INDEX **"
django-admin.py test multipleindex --settings=multipleindex_settings
echo ""

echo "** SPATIAL **"
django-admin.py test spatial --settings=spatial_settings
echo ""
