# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from decimal import Decimal

from mock import Mock

from django.template import TemplateDoesNotExist
from django.test import TestCase
from test_haystack.core.models import MockModel, MockTag, ManyToManyLeftSideModel, ManyToManyRightSideModel, \
    OneToManyLeftSideModel, OneToManyRightSideModel

from haystack.fields import *


class SearchFieldTestCase(TestCase):
    def test_get_iterable_objects_with_none(self):
        self.assertEqual([], SearchField.get_iterable_objects(None))

    def test_get_iterable_objects_with_single_non_iterable_object(self):
        obj = object()
        expected = [obj]

        self.assertEqual(expected, SearchField.get_iterable_objects(obj))

    def test_get_iterable_objects_with_list_stays_the_same(self):
        objects = [object(), object()]

        self.assertIs(objects, SearchField.get_iterable_objects(objects))

    def test_get_iterable_objects_with_django_manytomany_rel(self):
        left_model = ManyToManyLeftSideModel.objects.create()
        right_model_1 = ManyToManyRightSideModel.objects.create(name='Right side 1')
        right_model_2 = ManyToManyRightSideModel.objects.create()
        left_model.related_models.add(right_model_1)
        left_model.related_models.add(right_model_2)

        result = SearchField.get_iterable_objects(left_model.related_models)

        self.assertTrue(right_model_1 in result)
        self.assertTrue(right_model_2 in result)

    def test_get_iterable_objects_with_django_onetomany_rel(self):
        left_model = OneToManyLeftSideModel.objects.create()
        right_model_1 = OneToManyRightSideModel.objects.create(left_side=left_model)
        right_model_2 = OneToManyRightSideModel.objects.create(left_side=left_model)

        result = SearchField.get_iterable_objects(left_model.right_side)

        self.assertTrue(right_model_1 in result)
        self.assertTrue(right_model_2 in result)

    def test_resolve_attributes_lookup_with_field_that_points_to_none(self):
        related = Mock(spec=['none_field'], none_field=None)
        obj = Mock(spec=['related'], related=[related])

        field = SearchField(null=False)

        self.assertRaises(SearchFieldError, field.resolve_attributes_lookup, [obj], ['related', 'none_field'])

    def test_resolve_attributes_lookup_with_field_that_points_to_none_but_is_allowed_to_be_null(self):
        related = Mock(spec=['none_field'], none_field=None)
        obj = Mock(spec=['related'], related=[related])

        field = SearchField(null=True)

        self.assertEqual([None], field.resolve_attributes_lookup([obj], ['related', 'none_field']))

    def test_resolve_attributes_lookup_with_field_that_points_to_none_but_has_default(self):
        related = Mock(spec=['none_field'], none_field=None)
        obj = Mock(spec=['related'], related=[related])

        field = SearchField(default='Default value')

        self.assertEqual(['Default value'], field.resolve_attributes_lookup([obj], ['related', 'none_field']))

    def test_resolve_attributes_lookup_with_deep_relationship(self):
        related_lvl_2 = Mock(spec=['value'], value=1)
        related = Mock(spec=['related'], related=[related_lvl_2, related_lvl_2])
        obj = Mock(spec=['related'], related=[related])

        field = SearchField()

        self.assertEqual([1, 1], field.resolve_attributes_lookup([obj], ['related', 'related', 'value']))


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
        mock_tag = MockTag.objects.create(name='primary')

        mock = MockModel()
        mock.tag = mock_tag
        tag_name = CharField(model_attr='tag__name')

        self.assertEqual(tag_name.prepare(mock), u'primary')

        # Use the default.
        mock = MockModel()
        author = CharField(model_attr='author', default='')

        self.assertEqual(author.prepare(mock), u'')

        # Simulate failed lookups.
        mock_tag = MockTag.objects.create(name='primary')

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


class NgramFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = NgramField(model_attr='foo')
        except:
            self.fail()

        self.assertRaises(SearchFieldError, NgramField, faceted=True)

    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        author = NgramField(model_attr='user')

        self.assertEqual(author.prepare(mock), u'daniel')

        # Do a lookup through the relation.
        mock_tag = MockTag.objects.create(name='primary')

        mock = MockModel()
        mock.tag = mock_tag
        tag_name = NgramField(model_attr='tag__name')

        self.assertEqual(tag_name.prepare(mock), u'primary')

        # Use the default.
        mock = MockModel()
        author = NgramField(model_attr='author', default='')

        self.assertEqual(author.prepare(mock), u'')

        # Simulate failed lookups.
        mock_tag = MockTag.objects.create(name='primary')

        mock = MockModel()
        mock.tag = mock_tag
        tag_slug = NgramField(model_attr='tag__slug')

        self.assertRaises(SearchFieldError, tag_slug.prepare, mock)

        # Simulate default='foo'.
        mock = MockModel()
        default = NgramField(default='foo')

        self.assertEqual(default.prepare(mock), 'foo')

        # Simulate null=True.
        mock = MockModel()
        empty = NgramField(null=True)

        self.assertEqual(empty.prepare(mock), None)

        mock = MockModel()
        mock.user = None
        author = NgramField(model_attr='user', null=True)

        self.assertEqual(author.prepare(mock), None)


class EdgeNgramFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = EdgeNgramField(model_attr='foo')
        except:
            self.fail()

        self.assertRaises(SearchFieldError, EdgeNgramField, faceted=True)

    def test_prepare(self):
        mock = MockModel()
        mock.user = 'daniel'
        author = EdgeNgramField(model_attr='user')

        self.assertEqual(author.prepare(mock), u'daniel')

        # Do a lookup through the relation.
        mock_tag = MockTag.objects.create(name='primary')

        mock = MockModel()
        mock.tag = mock_tag
        tag_name = EdgeNgramField(model_attr='tag__name')

        self.assertEqual(tag_name.prepare(mock), u'primary')

        # Use the default.
        mock = MockModel()
        author = EdgeNgramField(model_attr='author', default='')

        self.assertEqual(author.prepare(mock), u'')

        # Simulate failed lookups.
        mock_tag = MockTag.objects.create(name='primary')

        mock = MockModel()
        mock.tag = mock_tag
        tag_slug = EdgeNgramField(model_attr='tag__slug')

        self.assertRaises(SearchFieldError, tag_slug.prepare, mock)

        # Simulate default='foo'.
        mock = MockModel()
        default = EdgeNgramField(default='foo')

        self.assertEqual(default.prepare(mock), 'foo')

        # Simulate null=True.
        mock = MockModel()
        empty = EdgeNgramField(null=True)

        self.assertEqual(empty.prepare(mock), None)

        mock = MockModel()
        mock.user = None
        author = EdgeNgramField(model_attr='user', null=True)

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
        mock_tag = MockTag.objects.create(name='primary')

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


class DecimalFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = DecimalField(model_attr='foo')
        except:
            self.fail()

    def test_prepare(self):
        mock = MockModel()
        mock.floaty = Decimal('12.5')
        floaty = DecimalField(model_attr='floaty')

        self.assertEqual(floaty.prepare(mock), '12.5')

        # Simulate default=1.5.
        mock = MockModel()
        default = DecimalField(default='1.5')

        self.assertEqual(default.prepare(mock), '1.5')

        # Simulate null=True.
        mock = MockModel()
        floaty_none = DecimalField(null=True)

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

    def test_convert(self):
        pub_date = DateField()
        self.assertEqual(pub_date.convert('2016-02-16'), datetime.date(2016, 2, 16))

    def test_prepare(self):
        mock = MockModel()
        mock.pub_date = datetime.date(2009, 2, 13)
        pub_date = DateField(model_attr='pub_date')

        self.assertEqual(pub_date.prepare(mock), datetime.date(2009, 2, 13))

        # Simulate default=datetime.date(2000, 1, 1).
        mock = MockModel()
        default = DateField(default=datetime.date(2000, 1, 1))

        self.assertEqual(default.prepare(mock), datetime.date(2000, 1, 1))

    def test_prepare_from_string(self):
        mock = MockModel()
        mock.pub_date = datetime.date(2016, 2, 16)
        pub_date = DateField(model_attr='pub_date')

        self.assertEqual(pub_date.prepare(mock), datetime.date(2016, 2, 16))


class DateTimeFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = DateTimeField(model_attr='foo')
        except:
            self.fail()

    def test_convert(self):
        pub_date = DateTimeField()

        self.assertEqual(pub_date.convert('2016-02-16T10:02:03'),
                         datetime.datetime(2016, 2, 16, 10, 2, 3))

    def test_prepare(self):
        mock = MockModel()
        mock.pub_date = datetime.datetime(2009, 2, 13, 10, 1, 0)
        pub_date = DateTimeField(model_attr='pub_date')

        self.assertEqual(pub_date.prepare(mock), datetime.datetime(2009, 2, 13, 10, 1, 0))

        # Simulate default=datetime.datetime(2009, 2, 13, 10, 01, 00).
        mock = MockModel()
        default = DateTimeField(default=datetime.datetime(2000, 1, 1, 0, 0, 0))

        self.assertEqual(default.prepare(mock), datetime.datetime(2000, 1, 1, 0, 0, 0))

    def test_prepare_from_string(self):
        mock = MockModel()
        mock.pub_date = '2016-02-16T10:01:02Z'
        pub_date = DateTimeField(model_attr='pub_date')

        self.assertEqual(pub_date.prepare(mock), datetime.datetime(2016, 2, 16, 10, 1, 2))


class MultiValueFieldTestCase(TestCase):
    def test_init(self):
        try:
            foo = MultiValueField(model_attr='foo')
        except:
            self.fail()

        self.assertRaises(SearchFieldError, MultiValueField, use_template=True)

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

    def test_convert_with_single_string(self):
        field = MultiValueField()

        self.assertEqual(['String'], field.convert('String'))

    def test_convert_with_single_int(self):
        field = MultiValueField()

        self.assertEqual([1], field.convert(1))

    def test_convert_with_list_of_strings(self):
        field = MultiValueField()

        self.assertEqual(['String 1', 'String 2'], field.convert(['String 1', 'String 2']))

    def test_convert_with_list_of_ints(self):
        field = MultiValueField()

        self.assertEqual([1, 2, 3], field.convert([1, 2, 3]))


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
