# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase
from test_haystack.core.forms import CustomChoiceFacetedSearchForm
from test_haystack.core.models import MockModel
from test_haystack.test_views import BasicAnotherMockModelSearchIndex, BasicMockModelSearchIndex

from haystack import connections
from haystack.forms import FacetedSearchForm, model_choices, ModelSearchForm, SearchForm
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.utils.loading import UnifiedIndex


class SearchFormTestCase(TestCase):
    def setUp(self):
        super(SearchFormTestCase, self).setUp()

        # Stow.
        self.old_unified_index = connections['default']._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections['default']._index = self.ui

        # Update the "index".
        backend = connections['default'].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections['default']._index = self.old_unified_index
        super(SearchFormTestCase, self).tearDown()

    def test_unbound(self):
        sf = SearchForm({}, searchqueryset=self.sqs)

        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)

        # This shouldn't blow up.
        sqs = sf.search()
        self.assertTrue(isinstance(sqs, EmptySearchQuerySet))


class ModelSearchFormTestCase(TestCase):
    def setUp(self):
        super(ModelSearchFormTestCase, self).setUp()
        # Stow.
        self.old_unified_index = connections['default']._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections['default']._index = self.ui

        # Update the "index".
        backend = connections['default'].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections['default']._index = self.old_unified_index
        super(ModelSearchFormTestCase, self).tearDown()

    def test_models_regression_1(self):
        # Regression for issue #1.
        msf = ModelSearchForm({
            'query': 'test',
            'models': ['core.mockmodel', 'core.anothermockmodel'],
        }, searchqueryset=self.sqs)

        self.assertEqual(msf.fields['models'].choices, [('core.anothermockmodel', u'Another mock models'), ('core.mockmodel', u'Mock models')])
        self.assertEqual(msf.errors, {})
        self.assertEqual(msf.is_valid(), True)

        sqs_with_models = msf.search()
        self.assertEqual(len(sqs_with_models.query.models), 2)

    def test_model_choices(self):
        self.assertEqual(len(model_choices()), 2)
        self.assertEqual([option[1] for option in model_choices()], [u'Another mock models', u'Mock models'])

    def test_model_choices_unicode(self):
        stowed_verbose_name_plural = MockModel._meta.verbose_name_plural
        MockModel._meta.verbose_name_plural = u'☃'
        self.assertEqual(len(model_choices()), 2)
        self.assertEqual([option[1] for option in model_choices()], [u'Another mock models', u'☃'])
        MockModel._meta.verbose_name_plural = stowed_verbose_name_plural


class FacetedSearchFormTestCase(TestCase):

    def setUp(self):
        super(FacetedSearchFormTestCase, self).setUp()
        # Stow.
        self.old_unified_index = connections['default']._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections['default']._index = self.ui

        # Update the "index".
        backend = connections['default'].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections['default']._index = self.old_unified_index
        super(FacetedSearchFormTestCase, self).tearDown()

    def test_init_with_selected_facets(self):
        sf = FacetedSearchForm({}, searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.fields['facets'].choices, [])
        self.assertEqual(sf.cleaned_data['facets'], [])

        sf = CustomChoiceFacetedSearchForm({}, searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.fields['facets'].choices, [
            ['author:daniel', 'author:daniel'],
            ['author:chris', 'author:chris']
        ])

        sf = CustomChoiceFacetedSearchForm(
            {'facets': ['author:daniel']}, searchqueryset=self.sqs
        )
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.fields['facets'].choices, [
            ['author:daniel', 'author:daniel'],
            ['author:chris', 'author:chris']
        ])
        self.assertEqual(sf.cleaned_data['facets'], ['author:daniel'])

        sf = CustomChoiceFacetedSearchForm(
            {'facets': ['author:daniel', 'author:chris']}, searchqueryset=self.sqs
        )
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.fields['facets'].choices, [
            ['author:daniel', 'author:daniel'],
            ['author:chris', 'author:chris']
        ])
        self.assertEqual(sf.cleaned_data['facets'], ['author:daniel', 'author:chris'])

    def test_search(self):
        sf = FacetedSearchForm({'q': 'test'}, searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())

        # Test the "skip no-colon" bits.
        sf = CustomChoiceFacetedSearchForm({'q': 'test', 'facets': ['authordaniel']}, searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())

        sf = CustomChoiceFacetedSearchForm({'q': 'test', 'facets': ['author:daniel']}, searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set([u'author:"daniel"']))

        sf = CustomChoiceFacetedSearchForm({'q': 'test', 'facets': ['author:daniel', 'author:chris']}, searchqueryset=self.sqs)
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set([u'author:"daniel"', u'author:"chris"']))
