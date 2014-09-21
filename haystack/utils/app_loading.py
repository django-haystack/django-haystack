# encoding: utf-8
from __future__ import absolute_import, print_function, unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__all__ = ['get_models', 'load_apps']


APP = 'app'
MODEL = 'model'


def is_app_or_model(label):
    label_bits = label.split('.')

    if len(label_bits) == 1:
        return APP
    elif len(label_bits) == 2:
        return MODEL
    else:
        raise ImproperlyConfigured("'%s' isn't recognized as an app (<app_label>) or model (<app_label>.<model_name>)." % label)


try:
    from django.apps import apps

    def load_apps():
        return [x.label for x in apps.get_app_configs()]

    def get_models(label):
        if is_app_or_model(label) == APP:
            try:
                app = apps.get_app_config(label)
            except LookupError as exc:
                raise ImproperlyConfigured(u'get_models() called for unregistered app %s: %s' % (label, exc))

            return app.get_models()
        else:
            app_label, model_name = label.split('.')
            return [apps.get_app_config(app_label).get_model(model_name)]

except ImportError:
    def load_apps():
        from django.db.models import get_app
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

    def get_models(label):
        from django.db.models import get_app, get_models as _get_models, get_model
        app_or_model = is_app_or_model(label)

        if app_or_model == APP:
            app_mod = get_app(label)
            return _get_models(app_mod)
        else:
            app_label, model_name = label.split('.')
            return [get_model(app_label, model_name)]
