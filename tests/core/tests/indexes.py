import datetime
from django.test import TestCase
from haystack.indexes import *
from core.models import MockModel, AThirdMockModel
from core.tests.mocks import MockSearchBackend


class BadSearchIndex1(SearchIndex):
    author = CharField(model_attr='author')
    pub_date = DateTimeField(model_attr='pub_date')


class BadSearchIndex2(SearchIndex):
    content = CharField(document=True, use_template=True)
    content2 = CharField(document=True, use_template=True)
    author = CharField(model_attr='author')
    pub_date = DateTimeField(model_attr='pub_date')


class GoodMockSearchIndex(SearchIndex):
    content = CharField(document=True, use_template=True)
    author = CharField(model_attr='author')
    pub_date = DateTimeField(model_attr='pub_date')
    extra = CharField(indexed=False, use_template=True)


# For testing inheritance...
class AltGoodMockSearchIndex(GoodMockSearchIndex):
    additional = CharField(model_attr='author')


class GoodCustomMockSearchIndex(SearchIndex):
    content = CharField(document=True, use_template=True)
    author = CharField(model_attr='author', faceted=True)
    pub_date = DateTimeField(model_attr='pub_date', faceted=True)
    extra = CharField(indexed=False, use_template=True)
    hello = CharField(model_attr='hello')
    
    def prepare(self, obj):
        super(GoodCustomMockSearchIndex, self).prepare(obj)
        self.prepared_data['whee'] = 'Custom preparation.'
        return self.prepared_data
    
    def prepare_author(self, obj):
        return "Hi, I'm %s" % self.prepared_data['author']
    
    def load_all_queryset(self):
        return self.model._default_manager.filter(id__gt=1)


class GoodNullableMockSearchIndex(SearchIndex):
    content = CharField(document=True, use_template=True)
    author = CharField(model_attr='author', null=True, faceted=True)


class GoodOverriddenFieldNameMockSearchIndex(SearchIndex):
    content = CharField(document=True, use_template=True, index_fieldname='more_content')
    author = CharField(model_attr='author', index_fieldname='name_s')
    hello = CharField(model_attr='hello')


class GoodFacetedMockSearchIndex(SearchIndex):
    content = CharField(document=True, use_template=True)
    author = CharField(model_attr='author')
    author_foo = FacetCharField(facet_for='author')
    pub_date = DateTimeField(model_attr='pub_date')
    pub_date_exact = FacetDateTimeField(facet_for='pub_date')
    
    def prepare_author(self, obj):
        return "Hi, I'm %s" % self.prepared_data['author']
    
    def prepare_pub_date_exact(self, obj):
        return "2010-10-26T01:54:32"


class SearchIndexTestCase(TestCase):
    def setUp(self):
        super(SearchIndexTestCase, self).setUp()
        self.msb = MockSearchBackend()
        self.mi = GoodMockSearchIndex(MockModel, backend=self.msb)
        self.cmi = GoodCustomMockSearchIndex(MockModel, backend=self.msb)
        self.cnmi = GoodNullableMockSearchIndex(MockModel, backend=self.msb)
        self.gfmsi = GoodFacetedMockSearchIndex(MockModel, backend=self.msb)
        self.sample_docs = {
            u'core.mockmodel.1': {
                'content': u'Indexed!\n1',
                'django_id': u'1',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n1',
                'author': u'daniel1',
                'pub_date': datetime.datetime(2009, 3, 17, 6, 0),
                'id': u'core.mockmodel.1'
            },
            u'core.mockmodel.2': {
                'content': u'Indexed!\n2',
                'django_id': u'2',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n2',
                'author': u'daniel2',
                'pub_date': datetime.datetime(2009, 3, 17, 7, 0),
                'id': u'core.mockmodel.2'
            },
            u'core.mockmodel.3': {
                'content': u'Indexed!\n3',
                'django_id': u'3',
                'django_ct': u'core.mockmodel',
                'extra': u'Stored!\n3',
                'author': u'daniel3',
                'pub_date': datetime.datetime(2009, 3, 17, 8, 0),
                'id': u'core.mockmodel.3'
            }
        }
    
    def test_no_contentfield_present(self):
        self.assertRaises(SearchFieldError, BadSearchIndex1, MockModel, MockSearchBackend())
    
    def test_too_many_contentfields_present(self):
        self.assertRaises(SearchFieldError, BadSearchIndex2, MockModel, MockSearchBackend())
    
    def test_contentfield_present(self):
        try:
            mi = GoodMockSearchIndex(MockModel, backend=MockSearchBackend())
        except:
            self.fail()
    
    def test_proper_fields(self):
        self.assertEqual(len(self.mi.fields), 4)
        self.assert_('content' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['content'], CharField))
        self.assert_('author' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['author'], CharField))
        self.assert_('pub_date' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['pub_date'], DateTimeField))
        self.assert_('extra' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['extra'], CharField))
        
        self.assertEqual(len(self.cmi.fields), 7)
        self.assert_('content' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['content'], CharField))
        self.assert_('author' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['author'], CharField))
        self.assert_('author_exact' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['author_exact'], FacetCharField))
        self.assert_('pub_date' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['pub_date'], DateTimeField))
        self.assert_('pub_date_exact' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['pub_date_exact'], FacetDateTimeField))
        self.assert_('extra' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['extra'], CharField))
        self.assert_('hello' in self.cmi.fields)
        self.assert_(isinstance(self.cmi.fields['extra'], CharField))
    
    def test_get_queryset(self):
        self.assertEqual(len(self.mi.get_queryset()), 3)
    
    def test_prepare(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.mi.prepare(mock)), 7)
        self.assertEqual(sorted(self.mi.prepare(mock).keys()), ['author', 'content', 'django_ct', 'django_id', 'extra', 'id', 'pub_date'])
    
    def test_custom_prepare(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
        
        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
    
    def test_custom_prepare_author(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
        
        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
        self.assertEqual(self.cmi.prepared_data['author'], "Hi, I'm daniel20")
        self.assertEqual(self.cmi.prepared_data['author_exact'], "Hi, I'm daniel20")
    
    def test_custom_model_attr(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.cmi.prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
        
        self.assertEqual(len(self.cmi.full_prepare(mock)), 11)
        self.assertEqual(sorted(self.cmi.full_prepare(mock).keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'extra', 'hello', 'id', 'pub_date', 'pub_date_exact', 'whee'])
        self.assertEqual(self.cmi.prepared_data['hello'], u'World!')
    
    def test_custom_index_fieldname(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        cofnmi = GoodOverriddenFieldNameMockSearchIndex(MockModel, backend=self.msb)
        self.assertEqual(len(cofnmi.prepare(mock)), 6)
        self.assertEqual(sorted(cofnmi.prepare(mock).keys()), ['django_ct', 'django_id', 'hello', 'id', 'more_content', 'name_s'])
        self.assertEqual(cofnmi.prepared_data['name_s'], u'daniel20')
        self.assertEqual(cofnmi.get_content_field(), 'more_content')
    
    def test_get_content_field(self):
        self.assertEqual(self.mi.get_content_field(), 'content')
    
    def test_update(self):
        self.mi.update()
        self.assertEqual(self.msb.docs, self.sample_docs)
        self.msb.clear()
    
    def test_update_object(self):
        self.assertEqual(self.msb.docs, {})
        
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.mi.update_object(mock)
        self.assertEqual(self.msb.docs, {'core.mockmodel.20': {'django_id': u'20', 'django_ct': u'core.mockmodel', 'author': u'daniel20', 'extra': u'Stored!\n20', 'content': u'Indexed!\n20', 'pub_date': datetime.datetime(2009, 1, 31, 4, 19), 'id': 'core.mockmodel.20'}})
        self.msb.clear()
    
    def test_remove_object(self):
        self.msb.docs = {'core.mockmodel.20': 'Indexed!\n20'}
        
        mock = MockModel()
        mock.pk = 20
        
        self.mi.remove_object(mock)
        self.assertEqual(self.msb.docs, {})
        self.msb.clear()
    
    def test_clear(self):
        self.msb.docs = {
            'core.mockmodel.1': 'Indexed!\n1',
            'core.mockmodel.2': 'Indexed!\n2',
            'core.mockmodel.20': 'Indexed!\n20',
        }
        
        self.mi.clear()
        self.assertEqual(self.msb.docs, {})
        self.msb.clear()
    
    def test_reindex(self):
        self.msb.docs = {
            'core.mockmodel.1': 'Indexed!\n1',
            'core.mockmodel.2': 'Indexed!\n2',
            'core.mockmodel.20': 'Indexed!\n20',
        }
        
        self.mi.reindex()
        self.assertEqual(self.msb.docs, self.sample_docs)
        self.msb.clear()
    
    def test_inheritance(self):
        try:
            agmi = AltGoodMockSearchIndex(MockModel, backend=self.msb)
        except:
            self.fail()
        
        self.assertEqual(len(agmi.fields), 5)
        self.assert_('content' in agmi.fields)
        self.assert_(isinstance(agmi.fields['content'], CharField))
        self.assert_('author' in agmi.fields)
        self.assert_(isinstance(agmi.fields['author'], CharField))
        self.assert_('pub_date' in agmi.fields)
        self.assert_(isinstance(agmi.fields['pub_date'], DateTimeField))
        self.assert_('extra' in agmi.fields)
        self.assert_(isinstance(agmi.fields['extra'], CharField))
        self.assert_('additional' in agmi.fields)
        self.assert_(isinstance(agmi.fields['additional'], CharField))
    
    def test_load_all_queryset(self):
        self.assertEqual([obj.id for obj in self.cmi.load_all_queryset()], [2, 3])
    
    def test_nullable(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = None
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        prepared_data = self.cnmi.prepare(mock)
        self.assertEqual(len(prepared_data), 6)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_exact', 'content', 'django_ct', 'django_id', 'id'])
        
        prepared_data = self.cnmi.full_prepare(mock)
        self.assertEqual(len(prepared_data), 4)
        self.assertEqual(sorted(prepared_data.keys()), ['content', 'django_ct', 'django_id', 'id'])
    
    def test_custom_facet_fields(self):
        mock = MockModel()
        mock.pk = 20
        mock.author = 'daniel'
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        prepared_data = self.gfmsi.prepare(mock)
        self.assertEqual(len(prepared_data), 8)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_foo', 'content', 'django_ct', 'django_id', 'id', 'pub_date', 'pub_date_exact'])
        
        prepared_data = self.gfmsi.full_prepare(mock)
        self.assertEqual(len(prepared_data), 8)
        self.assertEqual(sorted(prepared_data.keys()), ['author', 'author_foo', 'content', 'django_ct', 'django_id', 'id', 'pub_date', 'pub_date_exact'])
        self.assertEqual(prepared_data['author_foo'], u"Hi, I'm daniel")
        self.assertEqual(prepared_data['pub_date_exact'], '2010-10-26T01:54:32')


class BasicModelSearchIndex(ModelSearchIndex):
    class Meta:
        pass


class FieldsModelSearchIndex(ModelSearchIndex):
    class Meta:
        fields = ['author', 'pub_date']


class ExcludesModelSearchIndex(ModelSearchIndex):
    class Meta:
        excludes = ['author', 'foo']


class FieldsWithOverrideModelSearchIndex(ModelSearchIndex):
    foo = IntegerField(model_attr='foo')
    
    class Meta:
        fields = ['author', 'foo']
    
    def get_index_fieldname(self, f):
        if f.name == 'author':
            return 'author_bar'
        else:
            return f.name


class YetAnotherBasicModelSearchIndex(BasicModelSearchIndex):
    class Meta:
        pass


class ModelSearchIndexTestCase(TestCase):
    def setUp(self):
        super(ModelSearchIndexTestCase, self).setUp()
        self.msb = MockSearchBackend()
        self.bmsi = BasicModelSearchIndex(MockModel, backend=self.msb)
        self.fmsi = FieldsModelSearchIndex(MockModel, backend=self.msb)
        self.emsi = ExcludesModelSearchIndex(MockModel, backend=self.msb)
        self.fwomsi = FieldsWithOverrideModelSearchIndex(MockModel, backend=self.msb)
        self.yabmsi = YetAnotherBasicModelSearchIndex(AThirdMockModel, backend=self.msb)
    
    def test_basic(self):
        self.assertEqual(len(self.bmsi.fields), 4)
        self.assert_('foo' in self.bmsi.fields)
        self.assert_(isinstance(self.bmsi.fields['foo'], CharField))
        self.assertEqual(self.bmsi.fields['foo'].null, False)
        self.assertEqual(self.bmsi.fields['foo'].index_fieldname, 'foo')
        self.assert_('author' in self.bmsi.fields)
        self.assert_(isinstance(self.bmsi.fields['author'], CharField))
        self.assertEqual(self.bmsi.fields['author'].null, False)
        self.assert_('pub_date' in self.bmsi.fields)
        self.assert_(isinstance(self.bmsi.fields['pub_date'], DateTimeField))
        self.assert_(isinstance(self.bmsi.fields['pub_date'].default, datetime.datetime))
        self.assert_('text' in self.bmsi.fields)
        self.assert_(isinstance(self.bmsi.fields['text'], CharField))
        self.assertEqual(self.bmsi.fields['text'].document, True)
        self.assertEqual(self.bmsi.fields['text'].use_template, True)
    
    def test_fields(self):
        self.assertEqual(len(self.fmsi.fields), 3)
        self.assert_('author' in self.fmsi.fields)
        self.assert_(isinstance(self.fmsi.fields['author'], CharField))
        self.assert_('pub_date' in self.fmsi.fields)
        self.assert_(isinstance(self.fmsi.fields['pub_date'], DateTimeField))
        self.assert_('text' in self.fmsi.fields)
        self.assert_(isinstance(self.fmsi.fields['text'], CharField))
    
    def test_excludes(self):
        self.assertEqual(len(self.emsi.fields), 2)
        self.assert_('pub_date' in self.emsi.fields)
        self.assert_(isinstance(self.emsi.fields['pub_date'], DateTimeField))
        self.assert_('text' in self.emsi.fields)
        self.assert_(isinstance(self.emsi.fields['text'], CharField))
    
    def test_fields_with_override(self):
        self.assertEqual(len(self.fwomsi.fields), 3)
        self.assert_('author' in self.fwomsi.fields)
        self.assert_(isinstance(self.fwomsi.fields['author'], CharField))
        self.assert_('foo' in self.fwomsi.fields)
        self.assert_(isinstance(self.fwomsi.fields['foo'], IntegerField))
        self.assert_('text' in self.fwomsi.fields)
        self.assert_(isinstance(self.fwomsi.fields['text'], CharField))
    
    def test_overriding_field_name_with_get_index_fieldname(self):
        self.assert_(self.fwomsi.fields['foo'].index_fieldname, 'foo')
        self.assert_(self.fwomsi.fields['author'].index_fieldname, 'author_bar')
    
    def test_float_integer_fields(self):
        self.assertEqual(len(self.yabmsi.fields), 5)
        self.assertEqual(self.yabmsi.fields.keys(), ['average_delay', 'text', 'author', 'pub_date', 'view_count'])
        self.assert_('author' in self.yabmsi.fields)
        self.assert_(isinstance(self.yabmsi.fields['author'], CharField))
        self.assertEqual(self.yabmsi.fields['author'].null, False)
        self.assert_('pub_date' in self.yabmsi.fields)
        self.assert_(isinstance(self.yabmsi.fields['pub_date'], DateTimeField))
        self.assert_(isinstance(self.yabmsi.fields['pub_date'].default, datetime.datetime))
        self.assert_('text' in self.yabmsi.fields)
        self.assert_(isinstance(self.yabmsi.fields['text'], CharField))
        self.assertEqual(self.yabmsi.fields['text'].document, True)
        self.assertEqual(self.yabmsi.fields['text'].use_template, True)
        self.assert_('view_count' in self.yabmsi.fields)
        self.assert_(isinstance(self.yabmsi.fields['view_count'], IntegerField))
        self.assertEqual(self.yabmsi.fields['view_count'].null, False)
        self.assertEqual(self.yabmsi.fields['view_count'].index_fieldname, 'view_count')
        self.assert_('average_delay' in self.yabmsi.fields)
        self.assert_(isinstance(self.yabmsi.fields['average_delay'], FloatField))
        self.assertEqual(self.yabmsi.fields['average_delay'].null, False)
        self.assertEqual(self.yabmsi.fields['average_delay'].index_fieldname, 'average_delay')
