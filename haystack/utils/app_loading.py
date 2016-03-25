# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

__all__ = ['haystack_get_models', 'haystack_load_apps']

APP = 'app'
MODEL = 'model'


def haystack_get_app_modules():
    """Return the Python module for each installed app"""
    return [i.module for i in apps.get_app_configs()]

def haystack_load_apps():
    """Return a list of app labels for all installed applications which have models"""
    return [i.label for i in apps.get_app_configs() if i.models_module is not None]

def haystack_get_models(label):
    try:
        app_mod = apps.get_app_config(label)
        return app_mod.get_models()
    except LookupError:
        if '.' not in label:
            raise ImproperlyConfigured('Unknown application label {}'.format(label))
        app_label, model_name = label.rsplit('.', 1)
        return [apps.get_model(app_label, model_name)]
    except ImproperlyConfigured:
        pass

def haystack_get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)
