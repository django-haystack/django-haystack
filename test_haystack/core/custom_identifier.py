# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals


def get_identifier_method(key):
    """
    Custom get_identifier method used for testing the
    setting HAYSTACK_IDENTIFIER_MODULE
    """
    return key
