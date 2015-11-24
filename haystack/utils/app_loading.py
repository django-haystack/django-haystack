# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from haystack.utils import importlib

__all__ = ['haystack_get_models', 'haystack_load_apps']

APP = 'app'
MODEL = 'model'

if DJANGO_VERSION >= (1, 7):
    from django.apps import apps

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

else:
    from django.db.models.loading import get_app, get_model, get_models

    def is_app_or_model(label):
        label_bits = label.split('.')

        if len(label_bits) == 1:
            return APP
        elif len(label_bits) == 2:
            try:
                get_model(*label_bits)
            except LookupError:
                return APP
            return MODEL
        else:
            raise ImproperlyConfigured(
                "'%s' isn't recognized as an app (<app_label>) or model (<app_label>.<model_name>)." % label)

    def haystack_get_app_modules():
        """Return the Python module for each installed app"""
        return [importlib.import_module(i) for i in settings.INSTALLED_APPS]

    def haystack_load_apps():
        # Do all, in an INSTALLED_APPS sorted order.
        items = []

        for app in settings.INSTALLED_APPS:
            app_label = app.split('.')[-1]

            try:
                get_app(app_label)
            except ImproperlyConfigured:
                continue  # Intentionally allow e.g. apps without models.py

            items.append(app_label)

        return items

    def haystack_get_models(label):
        app_or_model = is_app_or_model(label)

        if app_or_model == APP:
            app_mod = get_app(label)
            return get_models(app_mod)
        else:
            app_label, model_name = label.rsplit('.', 1)
            return [get_model(app_label, model_name)]

    def haystack_get_model(app_label, model_name):
        return get_model(app_label, model_name)
