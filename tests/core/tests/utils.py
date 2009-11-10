from django.test import TestCase
from haystack.utils import get_identifier
from core.models import MockModel


class GetIdentifierTestCase(TestCase):
    def test_get_identifier(self):
        # Various invalid identifiers.
        self.assertRaises(AttributeError, get_identifier, 'core')
        self.assertRaises(AttributeError, get_identifier, 'core.mockmodel')
        self.assertRaises(AttributeError, get_identifier, 'core.mockmodel.foo')
        self.assertRaises(AttributeError, get_identifier, 'core-app.mockmodel.1')
        
        # Valid string identifier.
        self.assertEqual(get_identifier('core.mockmodel.1'), 'core.mockmodel.1')
        
        # Valid object.
        mock = MockModel.objects.get(pk=1)
        self.assertEqual(get_identifier(mock), 'core.mockmodel.1')
