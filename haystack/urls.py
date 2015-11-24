# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
from haystack.views import SearchView

try:
    from django.conf.urls import url
except ImportError:
    from django.conf.urls.defaults import url

urlpatterns = [
    url(r'^$', SearchView(), name='haystack_search'),
]
