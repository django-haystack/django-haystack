# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from haystack.constants import DEFAULT_ALIAS


class BaseRouter(object):
    # Reserved for future extension.
    pass


class DefaultRouter(BaseRouter):
    def for_read(self, **hints):
        return DEFAULT_ALIAS

    def for_write(self, **hints):
        return DEFAULT_ALIAS
