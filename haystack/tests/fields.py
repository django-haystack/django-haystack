import datetime
from django.template import TemplateDoesNotExist
from django.test import TestCase
from haystack.fields import *
from haystack.tests.mocks import MockModel, MockTemplateField


class CharFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, CharField)
        
        try:
            foo = CharField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.user = 'daniel'
        author = CharField(model_field='user')
        
        self.assertEqual(author.get_value(mock), u'daniel')

class IntegerFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, IntegerField)
        
        try:
            foo = IntegerField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.pk = 1
        pk = IntegerField(model_field='pk')
        
        self.assertEqual(pk.get_value(mock), 1)

class FloatFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, FloatField)
        
        try:
            foo = FloatField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.floaty = 12.5
        floaty = FloatField(model_field='floaty')
        
        self.assertEqual(floaty.get_value(mock), 12.5)

class BooleanFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, BooleanField)
        
        try:
            foo = BooleanField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.active = True
        is_active = BooleanField(model_field='active')
        
        self.assertEqual(is_active.get_value(mock), True)

class DateFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, DateField)
        
        try:
            foo = DateField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.pub_date = datetime.date(2009, 2, 13)
        pub_date = DateField(model_field='pub_date')
        
        self.assertEqual(pub_date.get_value(mock), datetime.date(2009, 2, 13))

class DateTimeFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, DateTimeField)
        
        try:
            foo = DateTimeField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.pub_date = datetime.datetime(2009, 2, 13, 10, 01, 00)
        pub_date = DateTimeField(model_field='pub_date')
        
        self.assertEqual(pub_date.get_value(mock), datetime.datetime(2009, 2, 13, 10, 01, 00))

class MultiValueFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(SearchFieldError, MultiValueField)
        
        try:
            foo = MultiValueField(model_field='foo')
        except:
            self.fail()
    
    def test_get_value(self):
        mock = MockModel()
        mock.sites = ['3', '4', '5']
        sites = MultiValueField(model_field='sites')
        
        self.assertEqual(sites.get_value(mock), ['3', '4', '5'])

class TemplateFieldTestCase(TestCase):
    def test_init(self):
        self.assertRaises(TypeError, TemplateField, model_field='foo')
        
        try:
            foo = TemplateField()
        except:
            self.fail()
        
        try:
            foo = TemplateField(template_name='foo.txt')
        except:
            self.fail()
        
        foo = TemplateField(template_name='foo.txt')
        self.assertEqual(foo.template_name, 'foo.txt')
    
    def test_get_value(self):
        mock = MockModel()
        mock.pk = 1
        mock.user = 'daniel'
        template1 = TemplateField()
        
        self.assertRaises(SearchFieldError, template1.get_value, mock)
        
        template2 = TemplateField()
        template2.instance_name = 'template'
        self.assertRaises(TemplateDoesNotExist, template2.get_value, mock)
        
        template3 = MockTemplateField()
        template3.instance_name = 'template'
        self.assertEqual(template3.get_value(mock), u'Indexed!\n1')


