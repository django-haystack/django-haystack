from django import forms
from django.db import models
import djangosearch
from djangosearch.query import SearchQuerySet


def model_choices():
    choices = [(m._meta, unicode(m._meta.verbose_name_plural)) for m in djangosearch.site.get_indexed_models()]
    return sorted(choices, key=lambda x: unicode(x._meta.verbose_name_plural))


class SearchForm(forms.Form):
    query = forms.CharField(required=False)
    
    def search(self):
        return SearchQuerySet.auto_query(self.cleaned_data['query'])


class ModelSearchForm(SearchForm):
    models = forms.MultipleChoiceField(choices=model_choices(), required=False, widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []
        
        for model in self.cleaned_data['models']:
            search_models.append(models.get_model(*model.split('.')))
        
        return search_models
    
    def search(self):
        return super(ModelSearchForm, self).search().models(self.get_models())
