from django import forms
from models import Restaurant

class RestaurantSearchForm(forms.Form):
    latitude = forms.CharField()
    longitude = forms.CharField()
    radius = forms.CharField()

    #add *_clean - validation methods here...
