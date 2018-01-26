# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from haystack.views import SearchView

urlpatterns = [
    url(r'^$', SearchView(), name='haystack_search'),
]
