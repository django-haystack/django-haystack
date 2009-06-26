from django.test import TestCase

class ManualSiteRegistrationTestCase(TestCase):
    def test_registrations(self):
        from haystack import backend
        sb = backend.SearchBackend()
        self.assertEqual(len(sb.site.get_indexed_models()), 2)
        
        from haystack import site
        self.assertEqual(len(site.get_indexed_models()), 2)
        
        from site_registration.models import Foo, Bar
        site.unregister(Bar)
        
        self.assertEqual(len(sb.site.get_indexed_models()), 1)
        self.assertEqual(len(site.get_indexed_models()), 1)
        
        site.unregister(Foo)
        
        self.assertEqual(len(sb.site.get_indexed_models()), 0)
        self.assertEqual(len(site.get_indexed_models()), 0)


class AutoSiteRegistrationTestCase(TestCase):
    urls = 'site_registration.auto_urls'
    
    def test_registrations(self):
        from haystack import backend
        sb = backend.SearchBackend()
        self.assertEqual(len(sb.site.get_indexed_models()), 2)
        
        from haystack import site
        self.assertEqual(len(site.get_indexed_models()), 2)
