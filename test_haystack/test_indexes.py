# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import time
from threading import Thread

from django.test import TestCase
from django.utils.six.moves import queue
from test_haystack.core.models import (AFifthMockModel, AThirdMockModel, MockModel, ManyToManyLeftSideModel,
                                       ManyToManyRightSideModel)

from haystack import connection_router, connections, indexes
from haystack.exceptions import SearchFieldError
from haystack.utils.loading import UnifiedIndex


class BadSearchIndex1(indexes.SearchIndex, indexes.Indexable):
    author = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class BadSearchIndex2(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    content2 = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return MockModel


class GoodMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')
    extra = indexes.CharField(indexed=False, use_template=True)

    def get_model(self):
        return MockModel


# For testing inheritance...
class AltGoodMockSearchIndex(GoodMockSearchIndex, indexes.Indexable):
    additional = indexes.CharField(model_attr='author')

    def get_model(self):
        return MockModel


class GoodCustomMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateTimeField(model_attr='pub_date', faceted=True)
    extra = indexes.CharField(indexed=False, use_template=True)
    hello = indexes.CharField(model_attr='hello')

    def prepare(self, obj):
        super(GoodCustomMockSearchIndex, self).prepare(obj)
        self.prepared_data['whee'] = 'Custom preparation.'
        return self.prepared_data

    def prepare_author(self, obj):
        return "Hi, I'm %s" % self.prepared_data['author']

    def load_all_queryset(self):
        return self.get_model()._default_manager.filter(id__gt=1)

    def get_model(self):
        return MockModel

    def index_queryset(self, using=None):
        return MockModel.objects.all()

    def read_queryset(self, using=None):
        return MockModel.objects.filter(author__in=['daniel1', 'daniel3'])

    def build_queryset(self, start_date=None, end_date=None):
        return MockModel.objects.filter(author__in=['daniel1', 'daniel3'])


class GoodNullableMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='author', null=True, faceted=True)

    def get_model(self):
        return MockModel


class GoodOverriddenFieldNameMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, index_fieldname='more_content')
    author = indexes.CharField(model_attr='author', index_fieldname='name_s')
    hello = indexes.CharField(model_attr='hello')

    def get_model(self):
        return MockModel


class GoodFacetedMockSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='author')
    author_foo = indexes.FacetCharField(facet_for='author')
    pub_date = indexes.DateTimeField(model_attr='pub_date')
    pub_date_exact = indexes.FacetDateTimeField(facet_for='pub_date')

    def get_model(self):
        return MockModel

    def prepare_author(self, obj):
        return "Hi, I'm %s" % self.prepared_data['author']

    def prepare_pub_date_exact(self, obj):
        return "2010-10-26T01:54:32"


class MROFieldsSearchIndexA(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='test_a')

    def get_model(self):
        return MockModel


class MROFieldsSearchIndexB(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='test_b')

    def get_model(self):
        return MockModel


class MROFieldsSearchChild(MROFieldsSearchIndexA, MROFieldsSearchIndexB):
    pass


class ModelWithManyToManyFieldAndAttributeLookupSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    related_models = indexes.MultiValueField(model_attr='related_models__name')

    def get_model(self):
        return ManyToManyLeftSideModel


class SearchIndexTestCase(TestCase):
    fixtures = ['base_data']

    def setUp(self):
        super(SearchIndexTestCase, self).setUp()
        self.sb = connections['default'].get_backend()
        self.mi = GoodMockSearchIndex()
        self.cmi = GoodCustomMockSearchIndex()
        self.cnmi = GoodNullableMockSearchIndex()
        self.gfmsi = GoodFacetedMockSearchIndex()

        # Fake the unified index.
        self.old_unified_index = connections['default']._index
        self.ui = UnifiedIndex()
        self.ui.build(indexes=[self.mi])
        connections['default']._index = self.ui

        self.sample_docs = {
            u'core.mockmodel.1': {
                'text': u'Indexed!\n1',
                'django_id': u'1',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n1',
                'author': u'daniel1',
                'pub_date': datetime.datetime(2009, 3, 17, 6, 0),
                'id': u'core.mockmodel.1'
            },
            u'core.mockmodel.2': {
                'text': u'Indexed!\n2',
                'django_id': u'2',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n2',
                'author': u'daniel2',
                'pub_date': datetime.datetime(2009, 3, 17, 7, 0),
                'id': u'core.mockmodel.2'
            },
            u'core.mockmodel.3': {
                'text': u'Indexed!\n3',
                'django_id': u'3',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n3',
                'author': u'daniel3',
                'pub_date': datetime.datetime(2009, 3, 17, 8, 0),
                'id': u'core.mockmodel.3'
            }
        }

    def tearDown(self):
        connections['default']._index = self.old_unified_index
        super(SearchIndexTestCase, self).tearDown()

    def test_no_contentfield_present(self):
        self.assertRaises(SearchFieldError, BadSearchIndex1)

    def test_too_many_contentfields_present(self):
        self.assertRaises(SearchFieldError, BadSearchIndex2)

    def test_contentfield_present(self):
        try:
            mi = GoodMockSearchIndex()
        except:
            self.fail()

    def test_proper_fields(self):
        self.assertEqual(len(self.mi.fields), 4)
        self.assertTrue('text' in self.mi.fields)
        self.assertTrue(isinstance(self.mi.fields['text'], indexes.CharField))
        self.assertTrue('author' in self.mi.fields)
        self.assertTrue(isinstance(self.mi.fields['author'], indexes.CharField))
        self.assertTrue('pub_date' in self.mi.fields)
        self.assertTrue(isinstance(self.mi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue('extra' in self.mi.fields)
        self.assertTrue(isinstance(self.mi.fields['extra'], indexes.CharField))

        self.assertEqual(len(self.cmi.fields), 7)
        self.assertTrue('text' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['text'], indexes.CharField))
        self.assertTrue('author' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['author'], indexes.CharField))
        self.assertTrue('author_exact' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['author_exact'], indexes.FacetCharField))
        self.assertTrue('pub_date' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue('pub_date_exact' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['pub_date_exact'], indexes.FacetDateTimeField))
        self.assertTrue('extra' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['extra'], indexes.CharField))
        self.assertTrue('hello' in self.cmi.fields)
        self.assertTrue(isinstance(self.cmi.fields['extra'], indexes.CharField))

    def test_index_queryset(self):
        self.assertEqual(len(self.cmi.index_queryset()), 3)

    def test_read_queryset(self):
        self.assertEqual(len(self.cmi.read_queryset()), 2)

    def test_build_queryset(self):
        # The custom SearchIndex.build_queryset returns the same records as
        # the read_queryset
        self.assertEqual(len(self.cmi.build_queryset()), 2)

        # Store a reference to the original method
        old_guf = self.mi.__class__.get_updated_field

        self.mi.__class__.get_updated_field = lambda self: 'pub_date'

        # With an updated field, we should get have filtered results
        sd = datetime.datetime(2009, 3, 17, 7, 0)
        self.assertEqual(len(self.mi.build_queryset(start_date=sd)), 2)

        ed = datetime.datetime(2009, 3, 17, 7, 59)
        self.assertEqual(len(self.mi.build_queryset(end_date=ed)), 2)

        sd = datetime.datetime(2009, 3, 17, 6, 0)
        ed = datetime.datetime(2009, 3, 17, 6, 59)
        self.assertEqual(len(self.mi.build_queryset(start_date=sd,
                                                    end_date=ed)), 1)

        # Remove the updated field for the next test
        del self.mi.__class__.get_updated_field

        # The default should return all 3 even if we specify a start date
        # because there is no updated field specified
        self.assertEqual(len(self.mi.build_queryset(start_date=sd)), 3)

        # Restore the original attribute
        self.mi.__class__.get_updated_field = old_guf


    def test_prepare(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.assertEqual(len(self.mi.prepare(mock)), 7)
        self.assertEqual(sorted(self.mi.prepare(mock).keys()), ['author', 'django_ct', 'django_id', 'extra', 'id', 'pub_date', 'text'])

    def test_custom_prepare(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])

        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])

    def test_thread_safety(self):
        # This is a regression. ``SearchIndex`` used to write to
        # ``self.prepared_data``, which would leak between threads if things
        # went too fast.
        exceptions = []

        def threaded_prepare(index_queue, index, model):
            try:
                index.queue = index_queue
                prepped = index.prepare(model)
            except Exception as e:
                exceptions.append(e)
                raise

        class ThreadedSearchIndex(GoodMockSearchIndex):
            def prepare_author(self, obj):
                if obj.pk == 20:
                    time.sleep(0.1)
                else:
                    time.sleep(0.5)

                index_queue.put(self.prepared_data['author'])
                return self.prepared_data['author']

        tmi = ThreadedSearchIndex()
        index_queue = queue.Queue()
        mock_1 = MockModel()
        mock_1.pk = 20
        mock_1.author = 'foo'
        mock_1.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        mock_2 = MockModel()
        mock_2.pk = 21
        mock_2.author = 'daniel%s' % mock_2.id
        mock_2.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        th1 = Thread(target=threaded_prepare, args=(index_queue, tmi, mock_1))
        th2 = Thread(target=threaded_prepare, args=(index_queue, tmi, mock_2))

        th1.start()
        th2.start()
        th1.join()
        th2.join()

        mock_1_result = index_queue.get()
        mock_2_result = index_queue.get()
        self.assertEqual(mock_1_result, u'foo')
        self.assertEqual(mock_2_result, u'daniel21')

    def test_custom_prepare_author(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])

        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])
        self.assertEqual(self.cmi.prepared_data['author'], "Hi, I'm daniel20")
        self.assertEqual(self.cmi.prepared_data['author_exact'], "Hi, I'm daniel20")

    def test_custom_model_attr(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])

        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'text', 'whee'])
        self.assertEqual(self.cmi.prepared_data['hello'], u'World!')

    def test_custom_index_fieldname(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        cofnmi = GoodOverriddenFieldNameMockSearchIndex()
        self.assertEqual(len(cofnmi.prepare(mock)), 6)
        self.assertEqual(sorted(cofnmi.prepare(mock).keys()), ['django_ct', 'django_id', 'hello', 'id', 'more_content', 'name_s'])
        self.assertEqual(cofnmi.prepared_data['name_s'], u'daniel20')
        self.assertEqual(cofnmi.get_content_field(), 'more_content')

    def test_get_content_field(self):
        self.assertEqual(self.mi.get_content_field(), 'text')

    def test_update(self):
        self.sb.clear()
        self.assertEqual(self.sb.search('*')['hits'], 0)
        self.mi.update()
        self.assertEqual(self.sb.search('*')['hits'], 3)
        self.sb.clear()

    def test_update_object(self):
        self.sb.clear()
        self.assertEqual(self.sb.search('*')['hits'], 0)

        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.mi.update_object(mock)
        self.assertEqual([(res.content_type(), res.pk) for res in self.sb.search('*')['results']], [(u'core.mockmodel', u'20')])
        self.sb.clear()

    def test_remove_object(self):
        self.mi.update()
        self.assertEqual(self.sb.search('*')['hits'], 3)

        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.mi.update_object(mock)
        self.assertEqual(self.sb.search('*')['hits'], 4)

        self.mi.remove_object(mock)
        self.assertEqual([(res.content_type(), res.pk) for res in self.sb.search('*')['results']], [(u'core.mockmodel', u'1'), (u'core.mockmodel', u'2'), (u'core.mockmodel', u'3')])

        # Put it back so we can test passing kwargs.
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        self.mi.update_object(mock)
        self.assertEqual(self.sb.search('*')['hits'], 4)

        self.mi.remove_object(mock, commit=False)
        self.assertEqual([(res.content_type(), res.pk) for res in self.sb.search('*')['results']], [(u'core.mockmodel', u'1'), (u'core.mockmodel', u'2'), (u'core.mockmodel', u'3'), (u'core.mockmodel', u'20')])

        self.sb.clear()

    def test_clear(self):
        self.mi.update()
        self.assertGreater(self.sb.search('*')['hits'], 0)

        self.mi.clear()
        self.assertEqual(self.sb.search('*')['hits'], 0)

    def test_reindex(self):
        self.mi.reindex()
        self.assertEqual([(res.content_type(), res.pk) for res in self.sb.search('*')['results']], [(u'core.mockmodel', u'1'), (u'core.mockmodel', u'2'), (u'core.mockmodel', u'3')])
        self.sb.clear()

    def test_inheritance(self):
        try:
            agmi = AltGoodMockSearchIndex()
        except:
            self.fail()

        self.assertEqual(len(agmi.fields), 5)
        self.assertTrue('text' in agmi.fields)
        self.assertTrue(isinstance(agmi.fields['text'], indexes.CharField))
        self.assertTrue('author' in agmi.fields)
        self.assertTrue(isinstance(agmi.fields['author'], indexes.CharField))
        self.assertTrue('pub_date' in agmi.fields)
        self.assertTrue(isinstance(agmi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue('extra' in agmi.fields)
        self.assertTrue(isinstance(agmi.fields['extra'], indexes.CharField))
        self.assertTrue('additional' in agmi.fields)
        self.assertTrue(isinstance(agmi.fields['additional'], indexes.CharField))

    def test_proper_field_resolution(self):
        mrofsc = MROFieldsSearchChild()
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        mock.test_a = 'This is A'
        mock.test_b = 'This is B'

        self.assertEqual(len(mrofsc.fields), 1)
        prepped_data = mrofsc.prepare(mock)
        self.assertEqual(len(prepped_data), 4)
        self.assertEqual(prepped_data['text'], 'This is A')

    def test_load_all_queryset(self):
        self.assertEqual([obj.id for obj in self.cmi.load_all_queryset()], [2, 3])

    def test_nullable(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = None
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        prepared_data = self.cnmi.prepare(mock)
        self.assertEqual(len(prepared_data), 6)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_exact', 'django_ct', 'django_id', 'id', 'text'])

        prepared_data = self.cnmi.full_prepare(mock)
        self.assertEqual(len(prepared_data), 4)
        self.assertEqual(sorted(prepared_data.keys()), ['django_ct', 'django_id', 'id', 'text'])

    def test_custom_facet_fields(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel'
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)

        prepared_data = self.gfmsi.prepare(mock)
        self.assertEqual(len(prepared_data), 8)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_foo', 'django_ct', 'django_id', 'id', 'pub_date', 'pub_date_exact', 'text'])

        prepared_data = self.gfmsi.full_prepare(mock)
        self.assertEqual(len(prepared_data), 8)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_foo', 'django_ct', 'django_id', 'id', 'pub_date', 'pub_date_exact', 'text'])
        self.assertEqual(prepared_data['author_foo'], u"Hi, I'm daniel")
        self.assertEqual(prepared_data['pub_date_exact'], '2010-10-26T01:54:32')


class BasicModelSearchIndex(indexes.ModelSearchIndex, indexes.Indexable):
    class Meta:
        model = MockModel


class FieldsModelSearchIndex(indexes.ModelSearchIndex, indexes.Indexable):
    class Meta:
        model = MockModel
        fields = ['author', 'pub_date']


class ExcludesModelSearchIndex(indexes.ModelSearchIndex, indexes.Indexable):
    class Meta:
        model = MockModel
        excludes = ['author', 'foo']


class FieldsWithOverrideModelSearchIndex(indexes.ModelSearchIndex, indexes.Indexable):
    foo = indexes.IntegerField(model_attr='foo')

    class Meta:
        model = MockModel
        fields = ['author', 'foo']

    def get_index_fieldname(self, f):
        if f.name == 'author':
            return 'author_bar'
        else:
            return f.name


class YetAnotherBasicModelSearchIndex(indexes.ModelSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)

    class Meta:
        model = AThirdMockModel


class GhettoAFifthMockModelSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)

    def get_model(self):
        return AFifthMockModel

    def index_queryset(self, using=None):
        # Index everything,
        return self.get_model().objects.complete_set()

    def read_queryset(self, using=None):
        return self.get_model().objects.all()


class ReadQuerySetTestSearchIndex(indexes.SearchIndex, indexes.Indexable):
    author = indexes.CharField(model_attr='author', document=True)

    def get_model(self):
        return AFifthMockModel

    def read_queryset(self, using=None):
        return self.get_model().objects.complete_set()


class TextReadQuerySetTestSearchIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(model_attr='author', document=True)

    def get_model(self):
        return AFifthMockModel

    def read_queryset(self, using=None):
        return self.get_model().objects.complete_set()


class ModelSearchIndexTestCase(TestCase):
    def setUp(self):
        super(ModelSearchIndexTestCase, self).setUp()
        self.sb = connections['default'].get_backend()
        self.bmsi = BasicModelSearchIndex()
        self.fmsi = FieldsModelSearchIndex()
        self.emsi = ExcludesModelSearchIndex()
        self.fwomsi = FieldsWithOverrideModelSearchIndex()
        self.yabmsi = YetAnotherBasicModelSearchIndex()

    def test_basic(self):
        self.assertEqual(len(self.bmsi.fields), 4)
        self.assertTrue('foo' in self.bmsi.fields)
        self.assertTrue(isinstance(self.bmsi.fields['foo'], indexes.CharField))
        self.assertEqual(self.bmsi.fields['foo'].null, False)
        self.assertEqual(self.bmsi.fields['foo'].index_fieldname, 'foo')
        self.assertTrue('author' in self.bmsi.fields)
        self.assertTrue(isinstance(self.bmsi.fields['author'], indexes.CharField))
        self.assertEqual(self.bmsi.fields['author'].null, False)
        self.assertTrue('pub_date' in self.bmsi.fields)
        self.assertTrue(isinstance(self.bmsi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue(isinstance(self.bmsi.fields['pub_date'].default, datetime.datetime))
        self.assertTrue('text' in self.bmsi.fields)
        self.assertTrue(isinstance(self.bmsi.fields['text'], indexes.CharField))
        self.assertEqual(self.bmsi.fields['text'].document, True)
        self.assertEqual(self.bmsi.fields['text'].use_template, True)

    def test_fields(self):
        self.assertEqual(len(self.fmsi.fields), 3)
        self.assertTrue('author' in self.fmsi.fields)
        self.assertTrue(isinstance(self.fmsi.fields['author'], indexes.CharField))
        self.assertTrue('pub_date' in self.fmsi.fields)
        self.assertTrue(isinstance(self.fmsi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue('text' in self.fmsi.fields)
        self.assertTrue(isinstance(self.fmsi.fields['text'], indexes.CharField))

    def test_excludes(self):
        self.assertEqual(len(self.emsi.fields), 2)
        self.assertTrue('pub_date' in self.emsi.fields)
        self.assertTrue(isinstance(self.emsi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue('text' in self.emsi.fields)
        self.assertTrue(isinstance(self.emsi.fields['text'], indexes.CharField))

    def test_fields_with_override(self):
        self.assertEqual(len(self.fwomsi.fields), 3)
        self.assertTrue('author' in self.fwomsi.fields)
        self.assertTrue(isinstance(self.fwomsi.fields['author'], indexes.CharField))
        self.assertTrue('foo' in self.fwomsi.fields)
        self.assertTrue(isinstance(self.fwomsi.fields['foo'], indexes.IntegerField))
        self.assertTrue('text' in self.fwomsi.fields)
        self.assertTrue(isinstance(self.fwomsi.fields['text'], indexes.CharField))

    def test_overriding_field_name_with_get_index_fieldname(self):
        self.assertTrue(self.fwomsi.fields['foo'].index_fieldname, 'foo')
        self.assertTrue(self.fwomsi.fields['author'].index_fieldname, 'author_bar')

    def test_float_integer_fields(self):
        self.assertEqual(len(self.yabmsi.fields), 5)
        self.assertEqual(sorted(self.yabmsi.fields.keys()), ['author', 'average_delay', 'pub_date', 'text', 'view_count'])
        self.assertTrue('author' in self.yabmsi.fields)
        self.assertTrue(isinstance(self.yabmsi.fields['author'], indexes.CharField))
        self.assertEqual(self.yabmsi.fields['author'].null, False)
        self.assertTrue('pub_date' in self.yabmsi.fields)
        self.assertTrue(isinstance(self.yabmsi.fields['pub_date'], indexes.DateTimeField))
        self.assertTrue(isinstance(self.yabmsi.fields['pub_date'].default, datetime.datetime))
        self.assertTrue('text' in self.yabmsi.fields)
        self.assertTrue(isinstance(self.yabmsi.fields['text'], indexes.CharField))
        self.assertEqual(self.yabmsi.fields['text'].document, True)
        self.assertEqual(self.yabmsi.fields['text'].use_template, False)
        self.assertTrue('view_count' in self.yabmsi.fields)
        self.assertTrue(isinstance(self.yabmsi.fields['view_count'], indexes.IntegerField))
        self.assertEqual(self.yabmsi.fields['view_count'].null, False)
        self.assertEqual(self.yabmsi.fields['view_count'].index_fieldname, 'view_count')
        self.assertTrue('average_delay' in self.yabmsi.fields)
        self.assertTrue(isinstance(self.yabmsi.fields['average_delay'], indexes.FloatField))
        self.assertEqual(self.yabmsi.fields['average_delay'].null, False)
        self.assertEqual(self.yabmsi.fields['average_delay'].index_fieldname, 'average_delay')


class ModelWithManyToManyFieldAndAttributeLookupSearchIndexTestCase(TestCase):
    def test_full_prepare(self):
        index = ModelWithManyToManyFieldAndAttributeLookupSearchIndex()

        left_model = ManyToManyLeftSideModel.objects.create()
        right_model_1 = ManyToManyRightSideModel.objects.create(name='Right side 1')
        right_model_2 = ManyToManyRightSideModel.objects.create()
        left_model.related_models.add(right_model_1)
        left_model.related_models.add(right_model_2)

        result = index.full_prepare(left_model)

        self.assertDictEqual(
            result,
            {
                'django_ct': 'core.manytomanyleftsidemodel',
                'django_id': '1',
                'text': None,
                'id': 'core.manytomanyleftsidemodel.1',
                'related_models': ['Right side 1', 'Default name'],
            }
        )
