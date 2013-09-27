from django.conf import settings
from django.test import TestCase
from haystack import connections, connection_router
from haystack.constants import DEFAULT_ALIAS
from haystack import indexes
from haystack.management.commands.build_solr_schema import Command
from haystack.query import SQ
from haystack.utils.loading import UnifiedIndex
from core.models import MockModel, AnotherMockModel


class MockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class AlteredInternalNamesTestCase(TestCase):
    def setUp(self):
        super(AlteredInternalNamesTestCase, self).setUp()

        self.old_ui = connections['default'].get_unified_index()
        ui = UnifiedIndex()
        ui.build(indexes=[MockModelSearchIndex()])
        connections['default']._index = ui

    def tearDown(self):
        connections['default']._index = self.old_ui
        super(AlteredInternalNamesTestCase, self).tearDown()

    def test_altered_names(self):
        sq = connections['default'].get_query()

        sq.add_filter(SQ(content='hello'))
        sq.add_model(MockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

        sq.add_model(AnotherMockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

    def test_solr_schema(self):
        command = Command()
        context_data = command.build_context(using=DEFAULT_ALIAS).dicts[-1]
        self.assertEqual(len(context_data), 6)
        self.assertEqual(context_data['DJANGO_ID'], 'my_django_id')
        self.assertEqual(context_data['content_field_name'], 'text')
        self.assertEqual(context_data['DJANGO_CT'], 'my_django_ct')
        self.assertEqual(context_data['default_operator'], 'AND')
        self.assertEqual(context_data['ID'], 'my_id')
        self.assertEqual(len(context_data['fields']), 3)
        self.assertEqual(sorted(context_data['fields'], key=lambda x: x['field_name']), [
            {
                'indexed': 'true',
                'type': 'text_en',
                'stored': 'true',
                'field_name': 'name',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'date',
                'stored': 'true',
                'field_name': 'pub_date',
                'multi_valued': 'false'
            },
            {
                'indexed': 'true',
                'type': 'text_en',
                'stored': 'true',
                'field_name': 'text',
                'multi_valued': 'false'
            },
        ])

        schema_xml = command.build_template(using=DEFAULT_ALIAS)
        self.assertTrue('<uniqueKey>my_id</uniqueKey>' in schema_xml)
        self.assertTrue('<field name="my_id" type="string" indexed="true" stored="true" multiValued="false" required="true"/>' in schema_xml)
        self.assertTrue('<field name="my_django_ct" type="string" indexed="true" stored="true" multiValued="false"/>' in schema_xml)
