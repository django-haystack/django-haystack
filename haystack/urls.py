# encoding: utf-8
from django.conf.urls import url

from haystack.views import SearchView

urlpatterns = [url(r"^$", SearchView(), name="haystack_search")]
