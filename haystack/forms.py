from django import forms
from django.db import models
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
import haystack
from haystack.query import SearchQuerySet


def model_choices(site=None):
    if site is None:
        site = haystack.sites.site
    
    choices = [("%s.%s" % (m._meta.app_label, m._meta.module_name), capfirst(unicode(m._meta.verbose_name_plural))) for m in site.get_indexed_models()]
    return sorted(choices, key=lambda x: x[1])


class SearchForm(forms.Form):
    q = forms.CharField(required=False, label=_('Search'))
    
    def __init__(self, *args, **kwargs):
        self.searchqueryset = kwargs.get('searchqueryset', None)
        self.load_all = kwargs.get('load_all', False)
        
        if self.searchqueryset is None:
            self.searchqueryset = SearchQuerySet()
        
        try:
            del(kwargs['searchqueryset'])
        except KeyError:
            pass
        
        try:
            del(kwargs['load_all'])
        except KeyError:
            pass
        
        super(SearchForm, self).__init__(*args, **kwargs)
    
    def search(self):
        self.clean()
        sqs = self.searchqueryset.auto_query(self.cleaned_data['q'])
        
        if self.load_all:
            sqs = sqs.load_all()
        
        return sqs


class HighlightedSearchForm(SearchForm):
    def search(self):
        return super(HighlightedSearchForm, self).search().highlight()


class FacetedSearchForm(SearchForm):
    selected_facets = forms.CharField(required=False, widget=forms.HiddenInput)
    
    def search(self):
        sqs = super(FacetedSearchForm, self).search()
        
        if self.cleaned_data['selected_facets']:
            sqs = sqs.narrow(self.cleaned_data['selected_facets'])
        
        return sqs


class ModelSearchForm(SearchForm):
    def __init__(self, *args, **kwargs):
        super(ModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(), required=False, label=_('Search In'), widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []
        
        for model in self.cleaned_data['models']:
            search_models.append(models.get_model(*model.split('.')))
        
        return search_models
    
    def search(self):
        sqs = super(ModelSearchForm, self).search()
        return sqs.models(*self.get_models())


class HighlightedModelSearchForm(ModelSearchForm):
    def search(self):
        return super(HighlightedModelSearchForm, self).search().highlight()


class FacetedModelSearchForm(ModelSearchForm):
    selected_facets = forms.CharField(required=False, widget=forms.HiddenInput)
    
    def search(self):
        sqs = super(FacetedModelSearchForm, self).search()
        
        if self.cleaned_data['selected_facets']:
            sqs = sqs.narrow(self.cleaned_data['selected_facets'])
        
        return sqs.models(*self.get_models())
