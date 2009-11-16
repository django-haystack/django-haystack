import pysolr
from django.conf import settings
from django.template import Template, Context
from django.test import TestCase
from haystack import indexes
from haystack.backends.solr_backend import SearchBackend
from haystack.sites import SearchSite
from core.models import MockModel


class MLTSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='foo')


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
        self.assertEqual(self.render(template, context), u'core.mockmodel.2 core.mockmodel.18 core.mockmodel.23 core.mockmodel.15 core.mockmodel.21 ')
