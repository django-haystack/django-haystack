import warnings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from haystack.utils import loading


class LoadBackendTestCase(TestCase):
    def test_load_solr(self):
        try:
            import pysolr
        except ImportError:
            warnings.warn("Pysolr doesn't appear to be installed. Unable to test loading the Solr backend.")
            return
        
        backend = loading.load_backend('haystack.backends.solr_backend.SolrEngine')
        self.assertEqual(backend.__name__, 'SolrEngine')
    
    def test_load_whoosh(self):
        try:
            import whoosh
        except ImportError:
            warnings.warn("Whoosh doesn't appear to be installed. Unable to test loading the Whoosh backend.")
            return
        
        backend = loading.load_backend('haystack.backends.whoosh_backend.WhooshEngine')
        self.assertEqual(backend.__name__, 'WhooshEngine')
    
    def test_load_simple(self):
        backend = loading.load_backend('haystack.backends.simple_backend.SimpleEngine')
        self.assertEqual(backend.__name__, 'SimpleEngine')
    
    def test_load_nonexistent(self):
        try:
            backend = loading.load_backend('foobar')
            self.fail()
        except ImproperlyConfigured, e:
            self.assertEqual(str(e), "The provided backend 'foobar' is not a complete Python path to a BaseEngine subclass.")
        
        try:
            backend = loading.load_backend('foobar.FooEngine')
            self.fail()
        except ImportError, e:
            pass
        
        try:
            backend = loading.load_backend('haystack.backends.simple_backend.FooEngine')
            self.fail()
        except ImportError, e:
            self.assertEqual(str(e), "The Python module 'haystack.backends.simple_backend' has no 'FooEngine' class.")
