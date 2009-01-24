from django import forms
from django.db import models
import djangosearch


def model_choices():
    # DRL_TODO: Alphabetize?
    return ((m._meta, unicode(m._meta.verbose_name_plural)) for m in djangosearch.site.get_indexed_models())


class ModelSearchForm(forms.Form):
    query = forms.CharField(required=False)
    models = forms.MultipleChoiceField(choices=model_choices(), required=False,
        widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []
        for model in self.cleaned_data['models']:
            search_models.append(models.get_model(*model.split('.')))
        if len(search_models) == 0:
            return None
        return search_models
