from django import forms
from django.db import models
import djangosearch
from djangosearch.query import SearchQuerySet


def model_choices(site=None):
    if site is None:
        site = djangosearch.site
    
    choices = [(m._meta, unicode(m._meta.verbose_name_plural)) for m in site.get_indexed_models()]
    return sorted(choices, key=lambda x: x[1])


class SearchForm(forms.Form):
    query = forms.CharField(required=False)
    
    def __init__(self, *args, **kwargs):
        self.searchqueryset = kwargs.get('searchqueryset', None)
        
        if self.searchqueryset is None:
            self.searchqueryset = SearchQuerySet()
        
        try:
            del(kwargs['searchqueryset'])
        except KeyError:
            pass
        
        super(SearchForm, self).__init__(*args, **kwargs)
    
    def search(self):
        self.clean()
        return self.searchqueryset.auto_query(self.cleaned_data['query'])


class ModelSearchForm(SearchForm):
    models = forms.MultipleChoiceField(choices=model_choices(), required=False, widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []
        
        for model in self.cleaned_data['models']:
            search_models.append(models.get_model(*model.split('.')))
        
        return search_models
    
    def search(self):
        sqs = super(ModelSearchForm, self).search()
        return sqs.models(self.get_models())
