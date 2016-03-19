# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack.views import SearchView

from django.conf.urls import url


urlpatterns = [
    url(r'^$', SearchView(), name='haystack_search'),
]
