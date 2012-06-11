from django.conf import settings
from django.test.utils import override_settings
from django.test.signals import setting_changed

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack import indexes
from haystack.management.commands.build_solr_schema import Command
from haystack.query import SQ
from haystack.utils.loading import UnifiedIndex
from haystack.utils.test import HaystackTestCase

from core.models import MockModel, AnotherMockModel


class MockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='foo', document=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return MockModel


def reset_connections(sender, setting, value, **kwargs):
    if setting == 'HAYSTACK_CONNECTIONS':
        connections.reset(settings.HAYSTACK_CONNECTIONS)

setting_changed.connect(reset_connections)


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS + [
        'overrides',
    ],
    HAYSTACK_CONNECTIONS={
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:9001/solr/test_default',
            'INCLUDE_SPELLING': True,
        },
    },
    HAYSTACK_ID_FIELD='my_id',
    HAYSTACK_DJANGO_CT_FIELD='my_django_ct',
    HAYSTACK_DJANGO_ID_FIELD='my_django_id')
class AlteredInternalNamesTestCase(HaystackTestCase):
    using = DEFAULT_ALIAS

    def setUp(self):
        super(AlteredInternalNamesTestCase, self).setUp()

        self.old_ui = connections[self.using].get_unified_index()
        ui = UnifiedIndex()
        ui.build(indexes=[MockModelSearchIndex()])
        connections[self.using]._index = ui

    def tearDown(self):
        connections[self.using]._index = self.old_ui
        super(AlteredInternalNamesTestCase, self).tearDown()

    def test_altered_names(self):
        sq = connections[self.using].get_query()

        sq.add_filter(SQ(content='hello'))
        sq.add_model(MockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

        sq.add_model(AnotherMockModel)
        self.assertEqual(sq.build_query(), u'(hello)')

    def test_solr_schema(self):
        command = Command()
        self.maxDiff = None
        self.assertEqual(command.build_context(using=DEFAULT_ALIAS).dicts[0], {
            'DJANGO_ID': 'my_django_id',
            'content_field_name': 'text',
            'fields': [
                {
                    'indexed': 'true',
                    'type': 'text_en',
                    'stored': 'true',
                    'field_name': 'text',
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
                    'field_name': 'name',
                    'multi_valued': 'false'
                }
            ],
            'DJANGO_CT': 'my_django_ct',
            'default_operator': 'AND',
            'ID': 'my_id'
        })

        schema_xml = command.build_template(using=DEFAULT_ALIAS)
        self.assertTrue('<uniqueKey>my_id</uniqueKey>' in schema_xml)
        self.assertTrue('<field name="my_id" type="string" indexed="true" stored="true" multiValued="false" required="true"/>' in schema_xml)
        self.assertTrue('<field name="my_django_ct" type="string" indexed="true" stored="true" multiValued="false"/>' in schema_xml)
