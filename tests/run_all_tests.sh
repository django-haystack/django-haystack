#!/bin/sh
echo "** CORE **"
django-admin.py test core --settings=settings
echo ""

echo "** SOLR **"
django-admin.py test solr_tests --settings=solr_settings
echo ""

echo "** WHOOSH **"
django-admin.py test whoosh_tests --settings=whoosh_settings
echo ""

echo "** SITE REG **"
django-admin.py test site_registration --settings=site_registration_settings