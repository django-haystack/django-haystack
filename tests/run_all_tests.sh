#!/bin/sh
echo "** CORE **"
django-admin.py test core --settings=settings
echo ""

echo "** SIMPLE **"
django-admin.py test simple_tests --settings=simple_settings
echo ""

echo "** SOLR **"
django-admin.py test solr_tests --settings=solr_settings
echo ""

echo "** WHOOSH **"
django-admin.py test whoosh_tests --settings=whoosh_settings
echo ""

echo "** SITE REG **"
django-admin.py test site_registration --settings=site_registration_settings

echo "** OVERRIDES **"
django-admin.py test overrides --settings=overrides_settings
echo ""
