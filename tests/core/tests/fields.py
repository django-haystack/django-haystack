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
        
        # Use the default.
        mock = MockModel()
        author = CharField(model_attr='author', default='')
        
        self.assertEqual(author.prepare(mock), u'')
        
        # Simulate failed lookups.
        mock_tag = MockTag(name='primary')
        mock = MockModel()
        mock.tag = mock_tag
        tag_slug = CharField(model_attr='tag__slug')
        
        self.assertRaises(SearchFieldError, tag_slug.prepare, mock)
        
        # Simulate default='foo'.
        mock = MockModel()
        default = CharField(default='foo')
        
        self.assertEqual(default.prepare(mock), 'foo')
        
        # Simulate null=True.
        mock = MockModel()
        empty = CharField(null=True)
        
        self.assertEqual(empty.prepare(mock), None)
        
        mock = MockModel()
        mock.user = None
        author = CharField(model_attr='user', null=True)
        
        self.assertEqual(author.prepare(mock), None)


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
        
        self.assertRaises(SearchFieldError, tag_count.prepare, mock)
        
        # Simulate default=1.
        mock = MockModel()
        default = IntegerField(default=1)
        
        self.assertEqual(default.prepare(mock), 1)
        
        # Simulate null=True.
        mock = MockModel()
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
        
        # Simulate default=1.5.
        mock = MockModel()
        default = FloatField(default=1.5)
        
        self.assertEqual(default.prepare(mock), 1.5)
        
        # Simulate null=True.
        mock = MockModel()
        floaty_none = FloatField(null=True)
        
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
        
        # Simulate default=True.
        mock = MockModel()
        default = BooleanField(default=True)
        
        self.assertEqual(default.prepare(mock), True)
        
        # Simulate null=True.
        mock = MockModel()
        booly_none = BooleanField(null=True)
        
        self.assertEqual(booly_none.prepare(mock), None)


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
        
        # Simulate default=datetime.date(2000, 1, 1).
        mock = MockModel()
        default = DateField(default=datetime.date(2000, 1, 1))
        
        self.assertEqual(default.prepare(mock), datetime.date(2000, 1, 1))


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
        
        # Simulate default=datetime.datetime(2009, 2, 13, 10, 01, 00).
        mock = MockModel()
        default = DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0, 0))
        
        self.assertEqual(default.prepare(mock), datetime.datetime(2000, 1, 1, 0, 0, 0))


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
        
        # Simulate default=[1].
        mock = MockModel()
        default = MultiValueField(default=[1])
        
        self.assertEqual(default.prepare(mock), [1])
        
        # Simulate null=True.
        mock = MockModel()
        multy_none = MultiValueField(null=True)
        
        self.assertEqual(multy_none.prepare(mock), None)


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
        
        # Test the select_template usage.
        foo = CharField(use_template=True, template_name=['bar.txt', 'foo.txt'])
        self.assertEqual(foo.template_name, ['bar.txt', 'foo.txt'])
    
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
        
        template4 = CharField(use_template=True, template_name='search/indexes/foo.txt')
        template4.instance_name = 'template'
        self.assertEqual(template4.prepare(mock), u'FOO!\n')
        
        template5 = CharField(use_template=True, template_name=['foo.txt', 'search/indexes/bar.txt'])
        template5.instance_name = 'template'
        self.assertEqual(template5.prepare(mock), u'BAR!\n')


##############################################################################
# The following tests look like they don't do much, but it's important because
# we need to verify that the faceted variants behave like the field they
# emulate. The old-broke behavior was convert everything to string.
##############################################################################


class FacetFieldTestCase(TestCase):
    def test_init(self):
        # You shouldn't use the FacetField itself.
        try:
            foo = FacetField(model_attr='foo')
            self.fail()
        except:
            pass
        
        try:
            foo_exact = FacetField(facet_for='bar')
            self.fail()
        except:
            pass


class FacetCharFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetCharField(model_attr='foo')
            foo_exact = FacetCharField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        author = FacetCharField(model_attr='user')
        
        self.assertEqual(author.prepare(mock), u'daniel')


class FacetIntegerFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetIntegerField(model_attr='foo')
            foo_exact = FacetIntegerField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.view_count = 13
        view_count = FacetIntegerField(model_attr='view_count')
        
        self.assertEqual(view_count.prepare(mock), 13)


class FacetFloatFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetFloatField(model_attr='foo')
            foo_exact = FacetFloatField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.price = 25.65
        price = FacetFloatField(model_attr='price')
        
        self.assertEqual(price.prepare(mock), 25.65)


class FacetBooleanFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetBooleanField(model_attr='foo')
            foo_exact = FacetBooleanField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.is_active = True
        is_active = FacetBooleanField(model_attr='is_active')
        
        self.assertEqual(is_active.prepare(mock), True)


class FacetDateFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetDateField(model_attr='foo')
            foo_exact = FacetDateField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.created = datetime.date(2010, 10, 30)
        created = FacetDateField(model_attr='created')
        
        self.assertEqual(created.prepare(mock), datetime.date(2010, 10, 30))


class FacetDateTimeFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetDateTimeField(model_attr='foo')
            foo_exact = FacetDateTimeField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.created = datetime.datetime(2010, 10, 30, 3, 14, 25)
        created = FacetDateTimeField(model_attr='created')
        
        self.assertEqual(created.prepare(mock), datetime.datetime(2010, 10, 30, 3, 14, 25))


class FacetMultiValueFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = FacetMultiValueField(model_attr='foo')
            foo_exact = FacetMultiValueField(facet_for='bar')
        except:
            self.fail()
        
        self.assertEqual(foo.facet_for, None)
        self.assertEqual(foo_exact.null, True)
        self.assertEqual(foo_exact.facet_for, 'bar')
    
    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        mock.sites = [1, 3, 4]
        sites = FacetMultiValueField(model_attr='sites')
        
        self.assertEqual(sites.prepare(mock), [1, 3, 4])
