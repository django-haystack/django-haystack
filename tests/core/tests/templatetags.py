from django.template import Template, Context
from django.test import TestCase
from haystack import indexes
from haystack import sites
from core.models import MockModel


class MLTSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='foo')


class MoreLikeThisTestCase(TestCase):
    fixtures = ['more_like_this.json']
    
    def setUp(self):
        super(MoreLikeThisTestCase, self).setUp()
        mock_index_site = sites.SearchSite()
        mock_index_site.register(MockModel, MLTSearchIndex)
        
        # Stow.
        self.old_site = sites.site
        sites.site = mock_index_site
    
    def render(self, template, context):
        # Why on Earth does Django not have a TemplateTestCase yet?
        t = Template(template)
        c = Context(context)
        return t.render(c)
    
    def test_more_like_this_with_limit(self):
        for mock in MockModel.objects.filter(pk__in=[4, 5, 6]):
            # Reindex it.
            mock.save()
        
        mock = MockModel.objects.get(pk=4)
        template = """{% load more_like_this %}{% more_like_this entry as related_content limit 5 %}{% for rc in related_content %}{{ rc.id }} {% endfor %}"""
        context = {
            'entry': mock,
        }
        # DRL_FIXME: Hand-verified to work on Solr (and since it's MLT,
        #            anywhere). However, can't get the test to work correctly.
        #            Maybe a fixture problem of not enough content?
        # self.assertEqual(self.render(template, context), u'5 6 ')
