import datetime
from django.db import models
from django.test import TestCase
from django.utils.encoding import force_unicode
from djangosearch.backends import BaseSearchBackend
from djangosearch import indexes


class MockIndexDefaultManager(object):
    def all(self):
        results = []
        
        for pk in xrange(3):
            mock = MockIndexModel()
            mock.id = pk
            mock.user = 'daniel%s' % pk
            mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
            results.append(mock)
        
        return results
            

class MockIndexModel(models.Model):
    _default_manager = MockIndexDefaultManager()


class MockSearchBackend(BaseSearchBackend):
    def __init__(self):
        self.docs = {}
    
    def update(self, index, iterable, commit=True):
        for obj in iterable:
            doc = {}
            doc['id'] = self.get_identifier(obj)
            doc['django_ct_s'] = "%s.%s" % (obj._meta.app_label, obj._meta.module_name)
            doc['django_id_s'] = force_unicode(obj.pk)
            
            for name, value in index.get_fields(obj):
                doc[name] = value
            
            self.docs[doc['id']] = doc

    def remove(self, obj, commit=True):
        del(self.docs[self.get_identifier(obj)])

    def clear(self, models, commit=True):
        self.docs = {}


class MockContentField(indexes.ContentField):
    def get_value(self, obj):
        return "Indexed!\n%s" % obj.pk


class MockStoredField(indexes.StoredField):
    def get_value(self, obj):
        return "Stored!\n%s" % obj.pk


class BadModelIndex1(indexes.ModelIndex):
    author = indexes.CharField('user')
    pub_date = indexes.DateTimeField('pub_date')


class BadModelIndex2(indexes.ModelIndex):
    content = indexes.ContentField()
    content2 = indexes.ContentField()
    author = indexes.CharField('user')
    pub_date = indexes.DateTimeField('pub_date')


class GoodMockModelIndex(indexes.ModelIndex):
    content = MockContentField()
    author = indexes.CharField('user')
    pub_date = indexes.DateTimeField('pub_date')
    extra = MockStoredField()


class ModelIndexTestCase(TestCase):
    def setUp(self):
        super(ModelIndexTestCase, self).setUp()
        self.msb = MockSearchBackend()
        self.mi = GoodMockModelIndex(MockIndexModel, backend=self.msb)
        self.sample_docs = {
            'tests.mockindexmodel.2': {
                'django_id_s': u'2', 
                'django_ct_s': 'tests.mockindexmodel', 
                'extra': u'Stored!\n2', 
                'author': u'daniel2', 
                'content': u'Indexed!\n2', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.2'
            }, 
            'tests.mockindexmodel.0': {
                'django_id_s': u'0', 
                'django_ct_s': 
                'tests.mockindexmodel', 
                'extra': u'Stored!\n0', 
                'author': u'daniel0', 
                'content': u'Indexed!\n0', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.0'
            }, 
            'tests.mockindexmodel.1': {
                'django_id_s': u'1', 
                'django_ct_s': 'tests.mockindexmodel', 
                'extra': u'Stored!\n1', 
                'author': u'daniel1', 
                'content': u'Indexed!\n1', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.1'
            },
        }
    
    def test_no_contentfield_present(self):
        self.assertRaises(indexes.SearchFieldError, BadModelIndex1, MockIndexModel, MockSearchBackend())
    
    def test_too_many_contentfields_present(self):
        self.assertRaises(indexes.SearchFieldError, BadModelIndex2, MockIndexModel, MockSearchBackend())
    
    def test_contentfield_present(self):
        try:
            mi = GoodMockModelIndex(GoodMockModelIndex, backend=MockSearchBackend())
        except:
            self.fail()
    
    def test_proper_fields(self):
        self.assertEqual(len(self.mi.fields), 4)
        self.assert_('content' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['content'], indexes.ContentField))
        self.assert_('author' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['author'], indexes.CharField))
        self.assert_('pub_date' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['pub_date'], indexes.DateTimeField))
        self.assert_('extra' in self.mi.fields)
        self.assert_(isinstance(self.mi.fields['extra'], indexes.StoredField))
    
    def test_get_query_set(self):
        self.assertEqual(len(self.mi.get_query_set()), 3)
    
    def test_get_fields(self):
        mock = MockIndexModel()
        mock.pk = 20
        mock.user = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(len(self.mi.get_fields(mock)), 4)
        self.assertEqual(sorted([field[0] for field in self.mi.get_fields(mock)]), ['author', 'content', 'extra', 'pub_date'])
    
    def test_update(self):
        self.mi.update()
        self.assertEqual(self.msb.docs, self.sample_docs)
        self.msb.clear([])
    
    def test_update_object(self):
        self.assertEqual(self.msb.docs, {})
        
        mock = MockIndexModel()
        mock.pk = 20
        mock.user = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.mi.update_object(mock)
        self.assertEqual(self.msb.docs, {'tests.mockindexmodel.20': {'django_id_s': u'20', 'django_ct_s': 'tests.mockindexmodel', 'author': u'daniel20', 'extra': u'Stored!\n20', 'content': u'Indexed!\n20', 'pub_date': u'2009-01-31 04:19:00', 'id': 'tests.mockindexmodel.20'}})
        self.msb.clear([])
    
    def test_remove_object(self):
        self.msb.docs = {'tests.mockindexmodel.20': 'Indexed!\n20'}
        
        mock = MockIndexModel()
        mock.pk = 20
        
        self.mi.remove_object(mock)
        self.assertEqual(self.msb.docs, {})
        self.msb.clear([])
    
    def test_clear(self):
        self.msb.docs = {
            'tests.mockindexmodel.1': 'Indexed!\n1',
            'tests.mockindexmodel.2': 'Indexed!\n2',
            'tests.mockindexmodel.20': 'Indexed!\n20',
        }
        
        self.mi.clear()
        self.assertEqual(self.msb.docs, {})
        self.msb.clear([])
    
    def test_reindex(self):
        docs = {
            'tests.mockindexmodel.2': {
                'django_id_s': u'2', 
                'django_ct_s': 'tests.mockindexmodel', 
                'extra': u'Stored!\n2', 
                'author': u'daniel2', 
                'content': u'Indexed!\n2', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.2'
            }, 
            'tests.mockindexmodel.0': {
                'django_id_s': u'0', 
                'django_ct_s': 
                'tests.mockindexmodel', 
                'extra': u'Stored!\n0', 
                'author': u'daniel0', 
                'content': u'Indexed!\n0', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.0'
            }, 
            'tests.mockindexmodel.1': {
                'django_id_s': u'1', 
                'django_ct_s': 'tests.mockindexmodel', 
                'extra': u'Stored!\n1', 
                'author': u'daniel1', 
                'content': u'Indexed!\n1', 
                'pub_date': u'2009-01-31 04:19:00', 
                'id': 'tests.mockindexmodel.1'
            },
        }
        self.msb.docs = docs
        
        self.mi.reindex()
        self.assertEqual(self.msb.docs, docs)
        self.msb.clear([])
