# encoding: utf-8
from django.urls import path

from haystack.views import SearchView

urlpatterns = [path("", SearchView(), name="haystack_search")]
