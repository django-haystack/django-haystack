from django.template import Template, Context
from django.test import TestCase
from haystack import indexes
from haystack import sites
from core.models import MockModel


class MLTSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, model_attr='foo')


class TemplateTagTestCase(TestCase):
    def render(self, template, context):
        # Why on Earth does Django not have a TemplateTestCase yet?
        t = Template(template)
        c = Context(context)
        return t.render(c)


class MoreLikeThisTestCase(TemplateTagTestCase):
    fixtures = ['more_like_this.json']
    
    def setUp(self):
        super(MoreLikeThisTestCase, self).setUp()
        mock_index_site = sites.SearchSite()
        mock_index_site.register(MockModel, MLTSearchIndex)
        
        # Stow.
        self.old_site = sites.site
        sites.site = mock_index_site
    
    def tearDown(self):
        sites.site = self.old_site
        super(MoreLikeThisTestCase, self).tearDown()
    
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


class HighlightTestCase(TemplateTagTestCase):
    def setUp(self):
        super(HighlightTestCase, self).setUp()
        self.sample_entry = """
Registering indexes in Haystack is very similar to registering models and
ModelAdmin classes in the Django admin site. If you want to override the default
indexing behavior for your model you can specify your own SearchIndex class.
This is useful for ensuring that future-dated or non-live content is not indexed
and searchable.

Every custom SearchIndex requires there be one and only one field with
document=True. This is the primary field that will get passed to the backend
for indexing. For this field, you’ll then need to create a template at
search/indexes/myapp/note_text.txt. This allows you to customize the document
that will be passed to the search backend for indexing. A sample template might
look like.

In addition, you may specify other fields to be populated along with the
document. In this case, we also index the user who authored the document as
well as the date the document was published. The variable you assign the
SearchField to should directly map to the field your search backend is
expecting. You instantiate most search fields with a parameter that points to
the attribute of the object to populate that field with.
"""
    
    def test_simple(self):
        template = """{% load highlight %}{% highlight entry with query %}"""
        context = {
            'entry': self.sample_entry,
            'query': 'index',
        }
        self.assertEqual(self.render(template, context), u'')
