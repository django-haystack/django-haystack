import datetime
from django.template import TemplateDoesNotExist
from django.test import TestCase
from haystack.fields import *
from core.models import MockModel, MockTag


class CharFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = CharField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        author = CharField(model_attr='user')
        
        self.assertEqual(author.prepare(mock), u'daniel')
        
        # Do a lookup through the relation.
        mock_tag = MockTag(name='primary')
        mock = MockModel()
        mock.tag = mock_tag
        tag_name = CharField(model_attr='tag__name')
        
        self.assertEqual(tag_name.prepare(mock), u'primary')
        
        # Simulate failed lookups.
        mock_tag = MockTag(name='primary')
        mock = MockModel()
        mock.tag = mock_tag
        tag_slug = CharField(model_attr='tag__slug')
        
        self.assertEqual(tag_slug.prepare(mock), u'')

class IntegerFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = IntegerField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.pk = 1
        pk = IntegerField(model_attr='pk')
        
        self.assertEqual(pk.prepare(mock), 1)
        
        # Simulate failed lookups.
        mock_tag = MockTag(name='primary')
        mock = MockModel()
        mock.tag = mock_tag
        tag_count = IntegerField(model_attr='tag__count')
        
        self.assertEqual(tag_count.prepare(mock), 0)
        
        # Simulate null=True.
        mock = MockModel()
        mock.pk = None
        pk_none = IntegerField(model_attr='pk', null=True)
        
        self.assertEqual(pk_none.prepare(mock), None)

class FloatFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FloatField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.floaty = 12.5
        floaty = FloatField(model_attr='floaty')
        
        self.assertEqual(floaty.prepare(mock), 12.5)
        
        # Simulate null=True.
        mock = MockModel()
        mock.floaty = None
        floaty_none = FloatField(model_attr='floaty', null=True)
        
        self.assertEqual(floaty_none.prepare(mock), None)

class BooleanFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = BooleanField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.active = True
        is_active = BooleanField(model_attr='active')
        
        self.assertEqual(is_active.prepare(mock), True)

class DateFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = DateField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.pub_date = datetime.date(2009, 2, 13)
        pub_date = DateField(model_attr='pub_date')
        
        self.assertEqual(pub_date.prepare(mock), datetime.date(2009, 2, 13))

class DateTimeFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = DateTimeField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.pub_date = datetime.datetime(2009, 2, 13, 10, 01, 00)
        pub_date = DateTimeField(model_attr='pub_date')
        
        self.assertEqual(pub_date.prepare(mock), datetime.datetime(2009, 2, 13, 10, 01, 00))

class MultiValueFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = MultiValueField(model_attr='foo')
        except:
            self.fail()
    
    def test_prepare(self):
        mock = MockModel()
        mock.sites = ['3', '4', '5']
        sites = MultiValueField(model_attr='sites')
        
        self.assertEqual(sites.prepare(mock), ['3', '4', '5'])

class CharFieldWithTemplateTestCase(TestCase):
    def test_init(self):
        try:
            foo = CharField(use_template=True)
        except:
            self.fail()
        
        try:
            foo = CharField(use_template=True, template_name='foo.txt')
        except:
            self.fail()
        
        foo = CharField(use_template=True, template_name='foo.txt')
        self.assertEqual(foo.template_name, 'foo.txt')
    
    def test_prepare(self):
        mock = MockModel()
        mock.pk = 1
        mock.user = 'daniel'
        template1 = CharField(use_template=True)
        
        self.assertRaises(SearchFieldError, template1.prepare, mock)
        
        template2 = CharField(use_template=True)
        template2.instance_name = 'template_x'
        self.assertRaises(TemplateDoesNotExist, template2.prepare, mock)
        
        template3 = CharField(use_template=True)
        template3.instance_name = 'template'
        self.assertEqual(template3.prepare(mock), u'Indexed!\n1')
