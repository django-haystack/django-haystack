import importlib
import re

from django.conf import settings

from haystack.constants import DJANGO_CT, DJANGO_ID, ID
from haystack.utils.highlighting import Highlighter # noqa=F401

IDENTIFIER_REGEX = re.compile(r"^[\w\d_]+\.[\w\d_]+\.[\w\d-]+$")


def default_get_identifier(obj_or_string):
    """
    Get an unique identifier for the object or a string representing the
    object.

    If not overridden, uses <app_label>.<object_name>.<pk>.
    """
    if isinstance(obj_or_string, str):
        if not IDENTIFIER_REGEX.match(obj_or_string):
            raise AttributeError(
                "Provided string '%s' is not a valid identifier." % obj_or_string
            )

        return obj_or_string

    return "%s.%s" % (get_model_ct(obj_or_string), obj_or_string._get_pk_val())


def _lookup_identifier_method():
    """
    If the user has set HAYSTACK_IDENTIFIER_METHOD, import it and return the method uncalled.
    If HAYSTACK_IDENTIFIER_METHOD is not defined, return haystack.utils.default_get_identifier.

    This always runs at module import time.  We keep the code in a function
    so that it can be called from unit tests, in order to simulate the re-loading
    of this module.
    """
    if not hasattr(settings, "HAYSTACK_IDENTIFIER_METHOD"):
        return default_get_identifier

    module_path, method_name = settings.HAYSTACK_IDENTIFIER_METHOD.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(
            "Unable to import module '%s' provided for HAYSTACK_IDENTIFIER_METHOD."
            % module_path
        )

    identifier_method = getattr(module, method_name, None)

    if not identifier_method:
        raise AttributeError(
            "Provided method '%s' for HAYSTACK_IDENTIFIER_METHOD does not exist in '%s'."
            % (method_name, module_path)
        )

    return identifier_method


get_identifier = _lookup_identifier_method()


def get_model_ct_tuple(model):
    # Deferred models should be identified as if they were the underlying model.
    model_name = (
        model._meta.concrete_model._meta.model_name
        if hasattr(model, "_deferred") and model._deferred
        else model._meta.model_name
    )
    return (model._meta.app_label, model_name)


def get_model_ct(model):
    return "%s.%s" % get_model_ct_tuple(model)


def get_facet_field_name(fieldname):
    if fieldname in [ID, DJANGO_ID, DJANGO_CT]:
        return fieldname

    return "%s_exact" % fieldname
