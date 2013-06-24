from __future__ import unicode_literals
import re

from django.conf import settings
from django.utils import six

from haystack.constants import ID, DJANGO_CT, DJANGO_ID
from haystack.utils.highlighting import Highlighter

try:
    from django.utils import importlib
except ImportError:
    import importlib

IDENTIFIER_REGEX = re.compile('^[\w\d_]+\.[\w\d_]+\.\d+$')


def default_get_identifier(obj_or_string):
    """
    Get an unique identifier for the object or a string representing the
    object.

    If not overridden, uses <app_label>.<object_name>.<pk>.
    """
    if isinstance(obj_or_string, six.string_types):
        if not IDENTIFIER_REGEX.match(obj_or_string):
            raise AttributeError(u"Provided string '%s' is not a valid identifier." % obj_or_string)

        return obj_or_string

    return u"%s.%s.%s" % (
        obj_or_string._meta.app_label,
        obj_or_string._meta.module_name,
        obj_or_string._get_pk_val()
    )


def _lookup_identifier_method():
    """
    If the user has set HAYSTACK_IDENTIFIER_METHOD, import it and return the method uncalled.
    If HAYSTACK_IDENTIFIER_METHOD is not defined, return haystack.utils.default_get_identifier.

    This always runs at module import time.  We keep the code in a function
    so that it can be called from unit tests, in order to simulate the re-loading
    of this module.
    """
    if not hasattr(settings, 'HAYSTACK_IDENTIFIER_METHOD'):
        return default_get_identifier

    module_path, method_name = settings.HAYSTACK_IDENTIFIER_METHOD.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(u"Unable to import module '%s' provided for HAYSTACK_IDENTIFIER_METHOD." % module_path)

    identifier_method = getattr(module, method_name, None)

    if not identifier_method:
        raise AttributeError(
            u"Provided method '%s' for HAYSTACK_IDENTIFIER_METHOD does not exist in '%s'." % (method_name, module_path)
        )

    return identifier_method


get_identifier = _lookup_identifier_method()


def get_model_ct(model):
    return "%s.%s" % (model._meta.app_label, model._meta.module_name)


def get_facet_field_name(fieldname):
    if fieldname in [ID, DJANGO_ID, DJANGO_CT]:
        return fieldname

    return "%s_exact" % fieldname
