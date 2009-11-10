from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
import haystack


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
