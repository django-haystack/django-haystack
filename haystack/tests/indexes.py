import datetime
from django.test import TestCase
from haystack import indexes
from haystack.tests.mocks import MockTemplateField, MockStoredTemplateField, MockTemplateField, MockModel, MockSearchBackend


class BadModelIndex1(indexes.ModelIndex):
    author = indexes.CharField(model_field='user')
    pub_date = indexes.DateTimeField(model_field='pub_date')


class BadModelIndex2(indexes.ModelIndex):
    content = indexes.TemplateField(document=True)
    content2 = indexes.TemplateField(document=True)
    author = indexes.CharField(model_field='user')
    pub_date = indexes.DateTimeField(model_field='pub_date')


class GoodMockModelIndex(indexes.ModelIndex):
    content = MockTemplateField(document=True)
    author = indexes.CharField(model_field='user')
    pub_date = indexes.DateTimeField(model_field='pub_date')
    extra = MockStoredTemplateField(indexed=False)


class ModelIndexTestCase(TestCase):
    def setUp(self):
        super(ModelIndexTestCase, self).setUp()
        self.msb = MockSearchBackend()
        self.mi = GoodMockModelIndex(MockModel, backend=self.msb)
        self.sample_docs = {
            'haystack.mockmodel.2': {
                'django_id_s': u'2',
                'django_ct_s': u'haystack.mockmodel', 
                'extra': u'Stored!\n2', 
                'author': u'daniel2', 
                'content': u'Indexed!\n2', 
                'pub_date': datetime.datetime(2009, 1, 31, 4, 19, 0), 
                'id': u'haystack.mockmodel.2'
            }, 
            'haystack.mockmodel.0': {
                'django_id_s': u'0',
                'django_ct_s': u'haystack.mockmodel', 
                'extra': u'Stored!\n0', 
                'author': u'daniel0', 
                'content': u'Indexed!\n0', 
                'pub_date': datetime.datetime(2009, 1, 31, 4, 19, 0), 
                'id': u'haystack.mockmodel.0'
            }, 
            'haystack.mockmodel.1': {
                'django_id_s': u'1',
                'django_ct_s': u'haystack.mockmodel', 
                'extra': u'Stored!\n1', 
                'author': u'daniel1', 
                'content': u'Indexed!\n1', 
                'pub_date': datetime.datetime(2009, 1, 31, 4, 19, 0), 
                'id': u'haystack.mockmodel.1'
            },
        }
    
    def test_no_contentfield_present(self):
        self.assertRaises(indexes.SearchFieldError, BadModelIndex1, MockModel, MockSearchBackend())
    
    def test_too_many_contentfields_present(self):
        self.assertRaises(indexes.SearchFieldError, BadModelIndex2, MockModel, MockSearchBackend())
    
    def test_contentfield_present(self):
        try:
            mi = GoodMockModelIndex(GoodMockModelIndex, backend=MockSearchBackend())
        except:
            self.fail()
    
    def test_proper_fields(self):
        self.assertEqual(len(self.mi.fields), 4)
        self.assert_('content' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['content'], indexes.TemplateField))
        self.assert_('author' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['author'], indexes.CharField))
        self.assert_('pub_date' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['pub_date'], indexes.DateTimeField))
        self.assert_('extra' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['extra'], indexes.TemplateField))
    
    def test_get_query_set(self):
        self.assertEqual(len(self.mi.get_query_set()), 3)
    
    def test_get_fields(self):
        mock = MockModel()
        mock.pk = 20
        mock.user = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.mi.get_fields(mock)), 4)
        self.assertEqual(sorted([field[0] for field in self.mi.get_fields(mock)]), ['author', 'content', 'extra', 'pub_date'])
    
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
        mock.user = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.mi.update_object(mock)
        self.assertEqual(self.msb.docs, {'haystack.mockmodel.20': {'django_id_s': u'20', 'django_ct_s': u'haystack.mockmodel', 'author': u'daniel20', 'extra': u'Stored!\n20', 'content': u'Indexed!\n20', 'pub_date': datetime.datetime(2009, 1, 31, 4, 19), 'id': 'haystack.mockmodel.20'}})
        self.msb.clear()
    
    def test_remove_object(self):
        self.msb.docs = {'haystack.mockmodel.20': 'Indexed!\n20'}
        
        mock = MockModel()
        mock.pk = 20
        
        self.mi.remove_object(mock)
        self.assertEqual(self.msb.docs, {})
        self.msb.clear()
    
    def test_clear(self):
        self.msb.docs = {
            'haystack.mockmodel.1': 'Indexed!\n1',
            'haystack.mockmodel.2': 'Indexed!\n2',
            'haystack.mockmodel.20': 'Indexed!\n20',
        }
        
        self.mi.clear()
        self.assertEqual(self.msb.docs, {})
        self.msb.clear()
    
    def test_reindex(self):
        self.msb.docs = {
            'haystack.mockmodel.1': 'Indexed!\n1',
            'haystack.mockmodel.2': 'Indexed!\n2',
            'haystack.mockmodel.20': 'Indexed!\n20',
        }
        
        self.mi.reindex()
        self.assertEqual(self.msb.docs, self.sample_docs)
        self.msb.clear()
