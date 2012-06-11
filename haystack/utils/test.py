from django.conf import settings
from django.test import TestCase
from haystack import connections


class HaystackTestCase(TestCase):

    def setUp(self):
        connections.reset(settings.HAYSTACK_CONNECTIONS)
        super(HaystackTestCase, self).setUp()
