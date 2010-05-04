from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
import haystack


class LoadBackendTestCase(TestCase):
    def test_load_solr(self):
        backend = haystack.load_backend('solr')
        self.assertEqual(backend.BACKEND_NAME, 'solr')
    
    def test_load_whoosh(self):
        backend = haystack.load_backend('whoosh')
        self.assertEqual(backend.BACKEND_NAME, 'whoosh')
    
    def test_load_dummy(self):
        backend = haystack.load_backend('dummy')
        self.assertEqual(backend.BACKEND_NAME, 'dummy')
    
    def test_load_simple(self):
        backend = haystack.load_backend('simple')
        self.assertEqual(backend.BACKEND_NAME, 'simple')
    
    def test_load_nonexistent(self):
        try:
            backend = haystack.load_backend('foobar')
            self.fail()
        except ImproperlyConfigured, e:
            self.assertEqual(str(e), "'foobar' isn't an available search backend. Available options are: 'dummy', 'simple', 'solr', 'whoosh'")
