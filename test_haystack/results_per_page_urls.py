# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from haystack.views import SearchView


class CustomPerPage(SearchView):
    results_per_page = 1


urlpatterns = [
    url(r'^search/$', CustomPerPage(load_all=False), name='haystack_search'),
    url(r'^search2/$', CustomPerPage(load_all=False, results_per_page=2), name='haystack_search'),
]
