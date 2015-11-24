# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack.routers import BaseRouter


class MultipleIndexRouter(BaseRouter):
    def for_write(self, instance=None, **hints):
        if instance and instance._meta.app_label == 'multipleindex':
            return 'solr'
