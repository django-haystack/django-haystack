import pysolr
from django.conf import settings
from django.template import Template, Context
from django.test import TestCase
from haystack.indexes import *
from haystack.backends.solr_backend import SearchBackend
from haystack.sites import SearchSite
from core.models import MockModel
try:
    set
except NameError:
    from sets import Set as set


class MLTSearchIndex(RealTimeSearchIndex):
    text = CharField(document=True, model_attr='foo')


class MoreLikeThisTagTestCase(TestCase):
    fixtures = ['bulk_data.json']
    
    def setUp(self):
        super(MoreLikeThisTagTestCase, self).setUp()
        
        self.raw_solr = pysolr.Solr(settings.HAYSTACK_SOLR_URL)
        self.raw_solr.delete(q='*:*')
        
        self.site = SearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = MLTSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, MLTSearchIndex)
        
        # Stow.
        import haystack
        self.old_site = haystack.site
        haystack.site = self.site
        
        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()
    
    def tearDown(self):
        import haystack
        haystack.site = self.old_site
        super(MoreLikeThisTagTestCase, self).tearDown()
    
    def render(self, template, context):
        # Why on Earth does Django not have a TemplateTestCase yet?
        t = Template(template)
        c = Context(context)
        return t.render(c)
    
    def test_more_like_this_with_limit(self):
        mock = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content limit 5 %}{% for rc in related_content %}{{ rc.id }} {% endfor %}"""
        context = {
            'entry': mock,
        }
        self.assertEqual(set(self.render(template, context).split()), set(u'core.mockmodel.2 core.mockmodel.18 core.mockmodel.23 core.mockmodel.15 core.mockmodel.21 '.split()))
    
    def test_more_like_this_without_limit(self):
        mock = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content %}{% for rc in related_content %}{{ rc.id }} {% endfor %}"""
        context = {
            'entry': mock,
        }
        self.assertEqual(set(self.render(template, context).split()), set(u'core.mockmodel.2 core.mockmodel.18 core.mockmodel.23 core.mockmodel.15 core.mockmodel.21 core.mockmodel.13 core.mockmodel.17 core.mockmodel.16 core.mockmodel.20 core.mockmodel.1 core.mockmodel.22 core.mockmodel.19 core.mockmodel.8 core.mockmodel.6 core.mockmodel.4 core.mockmodel.11 core.mockmodel.14 core.mockmodel.12 core.mockmodel.9 core.mockmodel.7 core.mockmodel.10 core.mockmodel.5'.split()))
