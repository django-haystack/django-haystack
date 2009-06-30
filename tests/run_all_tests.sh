#!/bin/sh
django-admin.py test core --settings=settings
django-admin.py test solr_tests --settings=solr_settings
django-admin.py test whoosh_tests --settings=whoosh_settings
django-admin.py test site_registration --settings=site_registration_settings