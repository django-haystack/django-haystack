# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import patterns, url

from .views import simple_view

urlpatterns = patterns('',
                       url(r'^simple-view$', simple_view, name='simple-view'))
