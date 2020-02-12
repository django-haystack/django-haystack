# -*- coding: utf-8 -*-
from django.test import TestCase
from test_haystack.core.models import AnotherMockModel, MockModel
from test_haystack.test_views import (
    BasicAnotherMockModelSearchIndex,
    BasicMockModelSearchIndex,
)

from haystack import connection_router, connections
from haystack.forms import FacetedSearchForm, ModelSearchForm, SearchForm, model_choices
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.utils.loading import UnifiedIndex


class SearchFormTestCase(TestCase):
    def setUp(self):
        super(SearchFormTestCase, self).setUp()

        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
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
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super(ModelSearchFormTestCase, self).tearDown()

    def test_models_regression_1(self):
        # Regression for issue #1.
        msf = ModelSearchForm(
            {"query": "test", "models": ["core.mockmodel", "core.anothermockmodel"]},
            searchqueryset=self.sqs,
        )

        self.assertEqual(
            msf.fields["models"].choices,
            [
                ("core.anothermockmodel", "Another mock models"),
                ("core.mockmodel", "Mock models"),
            ],
        )
        self.assertEqual(msf.errors, {})
        self.assertEqual(msf.is_valid(), True)

        sqs_with_models = msf.search()
        self.assertEqual(len(sqs_with_models.query.models), 2)

    def test_model_choices(self):
        self.assertEqual(len(model_choices()), 2)
        self.assertEqual(
            [option[1] for option in model_choices()],
            ["Another mock models", "Mock models"],
        )

    def test_model_choices_unicode(self):
        stowed_verbose_name_plural = MockModel._meta.verbose_name_plural
        MockModel._meta.verbose_name_plural = "☃"
        self.assertEqual(len(model_choices()), 2)
        self.assertEqual(
            [option[1] for option in model_choices()], ["Another mock models", "☃"]
        )
        MockModel._meta.verbose_name_plural = stowed_verbose_name_plural


class FacetedSearchFormTestCase(TestCase):
    def setUp(self):
        super(FacetedSearchFormTestCase, self).setUp()
        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

        self.sqs = SearchQuerySet()

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super(FacetedSearchFormTestCase, self).tearDown()

    def test_init_with_selected_facets(self):
        sf = FacetedSearchForm({}, searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, [])

        sf = FacetedSearchForm({}, selected_facets=[], searchqueryset=self.sqs)
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, [])

        sf = FacetedSearchForm(
            {}, selected_facets=["author:daniel"], searchqueryset=self.sqs
        )
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, ["author:daniel"])

        sf = FacetedSearchForm(
            {},
            selected_facets=["author:daniel", "author:chris"],
            searchqueryset=self.sqs,
        )
        self.assertEqual(sf.errors, {})
        self.assertEqual(sf.is_valid(), True)
        self.assertEqual(sf.selected_facets, ["author:daniel", "author:chris"])

    def test_search(self):
        sf = FacetedSearchForm(
            {"q": "test"}, selected_facets=[], searchqueryset=self.sqs
        )
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())

        # Test the "skip no-colon" bits.
        sf = FacetedSearchForm(
            {"q": "test"}, selected_facets=["authordaniel"], searchqueryset=self.sqs
        )
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set())

        sf = FacetedSearchForm(
            {"q": "test"}, selected_facets=["author:daniel"], searchqueryset=self.sqs
        )
        sqs = sf.search()
        self.assertEqual(sqs.query.narrow_queries, set(['author:"daniel"']))

        sf = FacetedSearchForm(
            {"q": "test"},
            selected_facets=["author:daniel", "author:chris"],
            searchqueryset=self.sqs,
        )
        sqs = sf.search()
        self.assertEqual(
            sqs.query.narrow_queries, set(['author:"daniel"', 'author:"chris"'])
        )
