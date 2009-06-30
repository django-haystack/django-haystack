import datetime
from django.test import TestCase
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
