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
    def setUp(self):
        super(AutoSiteRegistrationTestCase, self).setUp()
        
        # Stow.
        import haystack
        self.old_site = haystack.site
        test_site = haystack.sites.SearchSite()
        haystack.site = test_site
        
        haystack.autodiscover()
    
    def test_registrations(self):
        from haystack import backend
        sb = backend.SearchBackend()
        self.assertEqual(len(sb.site.get_indexed_models()), 2)
        
        from haystack import site
        self.assertEqual(len(site.get_indexed_models()), 2)
