# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack.views import SearchView

try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url



urlpatterns = patterns('haystack.views',
    url(r'^$', SearchView(), name='haystack_search'),
)
