# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.utils import get_model_ct
from haystack.utils.app_loading import haystack_get_model


def model_choices(using=DEFAULT_ALIAS):
    choices = [(get_model_ct(m), capfirst(smart_text(m._meta.verbose_name_plural)))
               for m in connections[using].get_unified_index().get_indexed_models()]
    return sorted(choices, key=lambda x: x[1])


class SearchForm(forms.Form):
    q = forms.CharField(required=False, label=_('Search'),
                        widget=forms.TextInput(attrs={'type': 'search'}))

    def __init__(self, *args, **kwargs):
        self.searchqueryset = kwargs.pop('searchqueryset', None)
        self.load_all = kwargs.pop('load_all', False)

        if self.searchqueryset is None:
            self.searchqueryset = SearchQuerySet()

        super(SearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        """
        Determines the behavior when no query was found.

        By default, no results are returned (``EmptySearchQuerySet``).

        Should you want to show all results, override this method in your
        own ``SearchForm`` subclass and do ``return self.searchqueryset.all()``.
        """
        return EmptySearchQuerySet()

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        if not self.cleaned_data.get('q'):
            return self.no_query_found()

        sqs = self.searchqueryset.auto_query(self.cleaned_data['q'])

        if self.load_all:
            sqs = sqs.load_all()

        return sqs

    def get_suggestion(self):
        if not self.is_valid():
            return None

        return self.searchqueryset.spelling_suggestion(self.cleaned_data['q'])


class HighlightedSearchForm(SearchForm):

    def search(self):
        return super(HighlightedSearchForm, self).search().highlight()


class FacetedSearchFormMixin(forms.Form):
    _facet_separator = ':'
    facets = forms.MultipleChoiceField(required=False, choices=[], widget=forms.MultipleHiddenInput)

    def get_facet_choices(self):
        return []

    def __init__(self, *args, **kwargs):
        super(FacetedSearchFormMixin, self).__init__(*args, **kwargs)
        facet_choices = self.get_facet_choices()
        for choice in facet_choices:
            if self._facet_separator not in choice[0]:
                raise ImproperlyConfigured("Facet choice values must take the form of 'field%svalue'" % self._facet_separator)

        self.fields['facets'].choices = facet_choices

    def search(self):
        sqs = super(FacetedSearchFormMixin, self).search()

        if not self.is_valid():
            return sqs

        # We need to process each facet to ensure that the field name and the
        # value are quoted correctly and separately:
        for facet in self.cleaned_data['facets']:
            if self._facet_separator not in facet:
                continue

            field, value = facet.split(self._facet_separator, 1)

            if value:
                sqs = sqs.narrow(u'%s:"%s"' % (field, sqs.query.clean(value)))

        return sqs


class FacetedSearchForm(FacetedSearchFormMixin, SearchForm):
    pass


class ModelSearchForm(SearchForm):

    def __init__(self, *args, **kwargs):
        super(ModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(), required=False, label=_('Search In'), widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return a list of the selected models."""
        search_models = []

        if self.is_valid():
            for model in self.cleaned_data['models']:
                search_models.append(haystack_get_model(*model.split('.')))

        return search_models

    def search(self):
        sqs = super(ModelSearchForm, self).search()
        return sqs.models(*self.get_models())


class HighlightedModelSearchForm(ModelSearchForm):

    def search(self):
        return super(HighlightedModelSearchForm, self).search().highlight()


class FacetedModelSearchForm(FacetedSearchFormMixin, ModelSearchForm):
    pass
