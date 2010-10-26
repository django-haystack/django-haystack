import datetime
from django.test import TestCase
from haystack.indexes import *
from haystack.exceptions import SearchFieldError
from haystack.fields import CharField
from haystack.sites import SearchSite, AlreadyRegistered, NotRegistered
from core.models import MockModel, AnotherMockModel


class MockNotAModel(object):
    pass


class FakeSearchIndex(BasicSearchIndex):
    def update_object(self, instance, **kwargs):
        # Incorrect behavior but easy to test and all we care about is that we
        # make it here. We rely on the `SearchIndex` tests to ensure correct
        # behavior.
        return True

    def remove_object(self, instance, **kwargs):
        # Incorrect behavior but easy to test and all we care about is that we
        # make it here. We rely on the `SearchIndex` tests to ensure correct
        # behavior.
        return True


class InvalidSearchIndex(SearchIndex):
    document = CharField(document=True)


class ValidSearchIndex(SearchIndex):
    text = CharField(document=True)
    author = CharField(index_fieldname='name')
    title = CharField(indexed=False)


class AlternateValidSearchIndex(SearchIndex):
    text = CharField(document=True)
    author = CharField(faceted=True)
    title = CharField(faceted=True)


class SearchSiteTestCase(TestCase):
    def setUp(self):
        super(SearchSiteTestCase, self).setUp()
        self.site = SearchSite()
    
    def test_register(self):
        self.assertRaises(AttributeError, self.site.register, MockNotAModel)
        
        self.site.register(MockModel)
        self.assertEqual(len(self.site._registry), 1)
        self.assert_(MockModel in self.site._registry)
        
        self.assertRaises(AlreadyRegistered, self.site.register, MockModel)
    
    def test_unregister(self):
        self.assertRaises(NotRegistered, self.site.unregister, MockModel)
        
        # Depends on proper function of register.
        self.site.register(MockModel)
        self.site.unregister(MockModel)
        self.assertEqual(len(self.site._registry), 0)
        self.assertFalse(MockModel in self.site._registry)
    
    def test_get_index(self):
        self.assertRaises(NotRegistered, self.site.get_index, MockModel)
        
        self.site.register(MockModel)
        self.assert_(isinstance(self.site.get_index(MockModel), BasicSearchIndex))
    
    def test_get_indexes(self):
        self.assertEqual(self.site.get_indexes(), {})
        
        self.site.register(MockModel)
        indexes = self.site.get_indexes()
        self.assert_(isinstance(indexes, dict))
        self.assertEqual(len(indexes), 1)
        self.assert_(MockModel in indexes)
    
    def test_get_indexed_models(self):
        self.assertEqual(self.site.get_indexed_models(), [])
        
        self.site.register(MockModel)
        indexed_models = self.site.get_indexed_models()
        self.assertEqual(len(indexed_models), 1)
        self.assert_(MockModel in indexed_models)
    
    def test_all_searchfields(self):
        self.site.register(MockModel)
        fields = self.site.all_searchfields()
        self.assertEqual(len(fields), 1)
        self.assert_('text' in fields)
        self.assert_(isinstance(fields['text'], CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, True)
        
        self.site.register(AnotherMockModel)
        fields = self.site.all_searchfields()
        self.assertEqual(len(fields), 1)
        self.assert_('text' in fields)
        self.assert_(isinstance(fields['text'], CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, True)
        
        self.site.unregister(AnotherMockModel)
        self.site.register(AnotherMockModel, AlternateValidSearchIndex)
        fields = self.site.all_searchfields()
        self.assertEqual(len(fields), 3)
        self.assertEqual(sorted(fields.keys()), ['author', 'text', 'title'])
        self.assert_('text' in fields)
        self.assert_(isinstance(fields['text'], CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, True)
        self.assert_('title' in fields)
        self.assert_(isinstance(fields['title'], CharField))
        self.assertEqual(fields['title'].document, False)
        self.assertEqual(fields['title'].use_template, False)
        self.assertEqual(fields['title'].faceted, True)
        self.assertEqual(fields['title'].indexed, True)
        self.assert_('author' in fields)
        self.assert_(isinstance(fields['author'], CharField))
        self.assertEqual(fields['author'].document, False)
        self.assertEqual(fields['author'].use_template, False)
        self.assertEqual(fields['author'].faceted, True)
        self.assertEqual(fields['author'].index_fieldname, 'author')
        
        self.site.unregister(MockModel)
        self.site.register(MockModel, ValidSearchIndex)
        fields = self.site.all_searchfields()
        self.assertEqual(len(fields), 4)
        self.assertEqual(sorted(fields.keys()), ['author', 'name', 'text', 'title'])
        self.assert_('text' in fields)
        self.assert_(isinstance(fields['text'], CharField))
        self.assertEqual(fields['text'].document, True)
        self.assertEqual(fields['text'].use_template, False)
        self.assert_('title' in fields)
        self.assert_(isinstance(fields['title'], CharField))
        self.assertEqual(fields['title'].document, False)
        self.assertEqual(fields['title'].use_template, False)
        self.assertEqual(fields['title'].faceted, True)
        self.assertEqual(fields['title'].indexed, True)
        self.assert_('author' in fields)
        self.assert_(isinstance(fields['author'], CharField))
        self.assertEqual(fields['author'].document, False)
        self.assertEqual(fields['author'].use_template, False)
        self.assertEqual(fields['author'].faceted, True)
        self.assertEqual(fields['author'].index_fieldname, 'author')
        self.assertEqual(fields['name'].document, False)
        self.assertEqual(fields['name'].use_template, False)
        self.assertEqual(fields['name'].faceted, False)
        self.assertEqual(fields['name'].index_fieldname, 'name')
        
        self.site.unregister(AnotherMockModel)
        self.site.register(AnotherMockModel, InvalidSearchIndex)
        self.assertRaises(SearchFieldError, self.site.all_searchfields)
    
    def test_get_index_fieldname(self):
        self.assertEqual(self.site._field_mapping, None)
        
        self.site.register(MockModel, ValidSearchIndex)
        self.site.register(AnotherMockModel)
        field = self.site.get_index_fieldname('text')
        self.assertEqual(self.site._field_mapping, {'text': 'text', 'title': 'title', 'author': 'name'})
        self.assertEqual(self.site.get_index_fieldname('text'), 'text')
        self.assertEqual(self.site.get_index_fieldname('author'), 'name')
        self.assertEqual(self.site.get_index_fieldname('title'), 'title')
        
        # Reset the internal state to test the invalid case.
        self.site._field_mapping = None
        self.assertEqual(self.site._field_mapping, None)
        
        self.site.unregister(AnotherMockModel)
        self.site.register(AnotherMockModel, AlternateValidSearchIndex)
        self.assertRaises(SearchFieldError, self.site.get_index_fieldname, 'text')
    
    def test_update_object(self):
        self.site.register(MockModel, FakeSearchIndex)
        
        mock = MockModel()
        mock.pk = 20
        mock.user = 'daniel%s' % mock.id
        mock.pub_date = datetime.datetime(2009, 1, 31, 4, 19, 0)
        
        self.assertEqual(self.site.update_object(mock), True)
    
    def test_remove_object(self):
        self.site.register(MockModel, FakeSearchIndex)
        
        mock = MockModel()
        mock.pk = 20
        
        self.assertEqual(self.site.remove_object(mock), True)
