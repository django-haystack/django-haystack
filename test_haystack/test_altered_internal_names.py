# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.test import TestCase
from test_haystack.core.models import AnotherMockModel, MockModel
from test_haystack.utils import check_solr

from haystack import connection_router, connections, constants, indexes
from haystack.management.commands.build_solr_schema import Command
from haystack.query import SQ
from haystack.utils.loading import UnifiedIndex


class MockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class AlteredInternalNamesTestCase(TestCase):
    def setUp(self):
        check_solr()
        super(AlteredInternalNamesTestCase, self).setUp()

        self.old_ui = connections['solr'].get_unified_index()
        ui = UnifiedIndex()
        ui.build(indexes=[MockModelSearchIndex()])
        connections['solr']._index = ui

        constants.ID  = 'my_id'
        constants.DJANGO_CT  = 'my_django_ct'
        constants.DJANGO_ID  = 'my_django_id'

    def tearDown(self):
        constants.ID  = 'id'
        constants.DJANGO_CT  = 'django_ct'
        constants.DJANGO_ID  = 'django_id'
        connections['solr']._index = self.old_ui
        super(AlteredInternalNamesTestCase, self).tearDown()

    def test_altered_names(self):
        sq = connections['solr'].get_query()

        sq.add_filter(SQ(content='hello'))
        sq.add_model(MockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

        sq.add_model(AnotherMockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

    def test_solr_schema(self):
        command = Command()
        context_data = command.build_context(using='solr').dicts[-1]
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

        schema_xml = command.build_template(using='solr')
        self.assertTrue('<uniqueKey>my_id</uniqueKey>' in schema_xml)
        self.assertTrue('<field name="my_id" type="string" indexed="true" stored="true" multiValued="false" required="true"/>' in schema_xml)
        self.assertTrue('<field name="my_django_ct" type="string" indexed="true" stored="true" multiValued="false"/>' in schema_xml)
