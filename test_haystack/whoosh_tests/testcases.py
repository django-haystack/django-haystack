# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shutil

from django.conf import settings
from django.test import TestCase


class WhooshTestCase(TestCase):
    fixtures = ['base_data']

    @classmethod
    def setUpClass(cls):
        for name, conn_settings in settings.HAYSTACK_CONNECTIONS.items():
            if conn_settings['ENGINE'] != 'haystack.backends.whoosh_backend.WhooshEngine':
                continue

            if 'STORAGE' in conn_settings and conn_settings['STORAGE'] != 'file':
                continue

            # Start clean
            if os.path.exists(conn_settings['PATH']):
                shutil.rmtree(conn_settings['PATH'])

            from haystack import connections
            connections[name].get_backend().setup()

        super(WhooshTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        for conn in settings.HAYSTACK_CONNECTIONS.values():
            if conn['ENGINE'] != 'haystack.backends.whoosh_backend.WhooshEngine':
                continue

            if 'STORAGE' in conn and conn['STORAGE'] != 'file':
                continue

            # Start clean
            if os.path.exists(conn['PATH']):
                shutil.rmtree(conn['PATH'])

        super(WhooshTestCase, cls).tearDownClass()
