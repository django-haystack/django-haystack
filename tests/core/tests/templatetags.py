# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import Template, Context
from django.test import TestCase
from haystack.utils import Highlighter


class BorkHighlighter(Highlighter):
    def render_html(self, highlight_locations=None, start_offset=None, end_offset=None):
        highlighted_chunk = self.text_block[start_offset:end_offset]
        
        for word in self.query_words:
            highlighted_chunk = highlighted_chunk.replace(word, 'Bork!')
        
        return highlighted_chunk


class TemplateTagTestCase(TestCase):
    def render(self, template, context):
        # Why on Earth does Django not have a TemplateTestCase yet?
        t = Template(template)
        c = Context(context)
        return t.render(c)


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
for indexing. For this field, you'll then need to create a template at
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
        self.assertEqual(self.render(template, context), u'...<span class="highlighted">index</span>ing behavior for your model you can specify your own Search<span class="highlighted">Index</span> class.\nThis is useful for ensuring that future-dated or non-live content is not <span class="highlighted">index</span>ed\nand searchable.\n\nEvery custom Search<span class="highlighted">Index</span> ...')
        
        template = """{% load highlight %}{% highlight entry with query html_tag "div" css_class "foo" max_length 100 %}"""
        context = {
            'entry': self.sample_entry,
            'query': 'field',
        }
        self.assertEqual(self.render(template, context), u'...<div class="foo">field</div> with\ndocument=True. This is the primary <div class="foo">field</div> that will get passed to the backend\nfor indexing...')
        
        template = """{% load highlight %}{% highlight entry with query html_tag "div" css_class "foo" max_length 100 %}"""
        context = {
            'entry': self.sample_entry,
            'query': 'Haystack',
        }
        self.assertEqual(self.render(template, context), u'...<div class="foo">Haystack</div> is very similar to registering models and\nModelAdmin classes in the Django admin site. If y...')
        
        template = """{% load highlight %}{% highlight "xxxxxxxxxxxxx foo bbxxxxx foo" with "foo" max_length 5 html_tag "span" %}"""
        context = {}
        self.assertEqual(self.render(template, context), u'...<span class="highlighted">foo</span> b...')
    
    def test_custom(self):
        # Stow.
        old_custom_highlighter = getattr(settings, 'HAYSTACK_CUSTOM_HIGHLIGHTER', None)
        settings.HAYSTACK_CUSTOM_HIGHLIGHTER = 'core.tests.FooHighlighter'
        
        template = """{% load highlight %}{% highlight entry with query %}"""
        context = {
            'entry': self.sample_entry,
            'query': 'index',
        }
        self.assertRaises(ImproperlyConfigured, self.render, template, context)
        
        settings.HAYSTACK_CUSTOM_HIGHLIGHTER = 'core.tests.templatetags.BorkHighlighter'
        
        template = """{% load highlight %}{% highlight entry with query %}"""
        context = {
            'entry': self.sample_entry,
            'query': 'index',
        }
        self.assertEqual(self.render(template, context), u'Bork!ing behavior for your model you can specify your own SearchIndex class.\nThis is useful for ensuring that future-dated or non-live content is not Bork!ed\nand searchable.\n\nEvery custom SearchIndex ')
        
        # Restore.
        settings.HAYSTACK_CUSTOM_HIGHLIGHTER = None
