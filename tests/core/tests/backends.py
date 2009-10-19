import datetime
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
import haystack
from haystack.backends import BaseSearchBackend
from core.models import MockModel, AnotherMockModel


class BaseSearchBackendTestCase(TestCase):
    def setUp(self):
        super(BaseSearchBackendTestCase, self).setUp()
        self.bsb = BaseSearchBackend()
    
    def test_get_identifier(self):
        # Various invalid identifiers.
        self.assertRaises(AttributeError, self.bsb.get_identifier, 'core')
        self.assertRaises(AttributeError, self.bsb.get_identifier, 'core.mockmodel')
        self.assertRaises(AttributeError, self.bsb.get_identifier, 'core.mockmodel.foo')
        self.assertRaises(AttributeError, self.bsb.get_identifier, 'core-app.mockmodel.1')
        
        # Valid string identifier.
        self.assertEqual(self.bsb.get_identifier('core.mockmodel.1'), 'core.mockmodel.1')
        
        # Valid object.
        mock = MockModel.objects.get(pk=1)
        self.assertEqual(self.bsb.get_identifier(mock), 'core.mockmodel.1')


class LoadBackendTestCase(TestCase):
    def load_solr(self):
        backend = haystack.load_backend('solr')
        self.assertEqual(backend.BACKEND_NAME, 'solr')
    
    def load_whoosh(self):
        backend = haystack.load_backend('whoosh')
        self.assertEqual(backend.BACKEND_NAME, 'whoosh')
    
    def load_dummy(self):
        backend = haystack.load_backend('dummy')
        self.assertEqual(backend.BACKEND_NAME, 'dummy')
    
    def load_nonexistent(self):
        try:
            backend = haystack.load_backend('foobar')
            self.fail()
        except ImproperlyConfigured:
            pass
