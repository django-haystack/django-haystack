from django.contrib.webdesign import lorem_ipsum
from django.template import Template, Context
from django.test import TestCase

from haystack import connections
from haystack import indexes
from haystack.utils.loading import UnifiedIndex

from core.models import MockModel
from solr_tests.tests.solr_backend import clear_solr_index


class MLTSearchIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='foo')

    def get_model(self):
        return MockModel


class MoreLikeThisTagTestCase(TestCase):
    fixtures = ['bulk_data.json']

    def setUp(self):
        super(MoreLikeThisTagTestCase, self).setUp()

        clear_solr_index()

        # Stow.
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.smmi = MLTSearchIndex()
        self.ui.build(indexes=[self.smmi])
        connections['default']._index = self.ui

        def restore_globals():
            connections['default']._index = self.old_ui

        self.addCleanup(restore_globals)

        # Force indexing of the content.
        for mock in MockModel.objects.all():
            mock.save()

        # Create one test record which shouldn't match anything at all:
        MockModel.objects.create(author="test_bogon",
                                 foo=lorem_ipsum.paragraphs(3),
                                 tag_id=1)

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

        self.assertEqual(set(self.render(template, context).split()),
                         set(u'core.mockmodel.2 core.mockmodel.18 core.mockmodel.23 core.mockmodel.15 core.mockmodel.8'.split()))

    def test_more_like_this_without_limit(self):
        mock = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content %}{% for rc in related_content %}{{ rc.id }} {% endfor %}"""
        context = {
            'entry': mock,
        }

        # Our test objects are very similar and will match every other record:
        mock_pks = MockModel.objects.exclude(pk=mock.pk).exclude(author="test_bogon")
        mock_pks = mock_pks.values_list("pk", flat=True)

        rendered_ids = set(self.render(template, context).split())

        self.assertEqual(rendered_ids, set("core.mockmodel.%s" % i for i in mock_pks))
