# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import inspect
import threading
import warnings
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.module_loading import module_has_submodule

from haystack import constants
from haystack.exceptions import NotHandled, SearchFieldError
from haystack.utils import importlib
from haystack.utils.app_loading import haystack_get_app_modules


def import_class(path):
    path_bits = path.split('.')
    # Cut off the class name at the end.
    class_name = path_bits.pop()
    module_path = '.'.join(path_bits)
    module_itself = importlib.import_module(module_path)

    if not hasattr(module_itself, class_name):
        raise ImportError("The Python module '%s' has no '%s' class." % (module_path, class_name))

    return getattr(module_itself, class_name)


# Load the search backend.
def load_backend(full_backend_path):
    """
    Loads a backend for interacting with the search engine.

    Requires a ``backend_path``. It should be a string resembling a Python
    import path, pointing to a ``BaseEngine`` subclass. The built-in options
    available include::

      * haystack.backends.solr.SolrEngine
      * haystack.backends.xapian.XapianEngine (third-party)
      * haystack.backends.whoosh.WhooshEngine
      * haystack.backends.simple.SimpleEngine

    If you've implemented a custom backend, you can provide the path to
    your backend & matching ``Engine`` class. For example::

      ``myapp.search_backends.CustomSolrEngine``

    """
    path_bits = full_backend_path.split('.')

    if len(path_bits) < 2:
        raise ImproperlyConfigured("The provided backend '%s' is not a complete Python path to a BaseEngine subclass." % full_backend_path)

    return import_class(full_backend_path)


def load_router(full_router_path):
    """
    Loads a router for choosing which connection to use.

    Requires a ``full_router_path``. It should be a string resembling a Python
    import path, pointing to a ``BaseRouter`` subclass. The built-in options
    available include::

      * haystack.routers.DefaultRouter

    If you've implemented a custom backend, you can provide the path to
    your backend & matching ``Engine`` class. For example::

      ``myapp.search_routers.MasterSlaveRouter``

    """
    path_bits = full_router_path.split('.')

    if len(path_bits) < 2:
        raise ImproperlyConfigured("The provided router '%s' is not a complete Python path to a BaseRouter subclass." % full_router_path)

    return import_class(full_router_path)


class ConnectionHandler(object):
    def __init__(self, connections_info):
        self.connections_info = connections_info
        self.thread_local = threading.local()
        self._index = None

    def ensure_defaults(self, alias):
        try:
            conn = self.connections_info[alias]
        except KeyError:
            raise ImproperlyConfigured("The key '%s' isn't an available connection." % alias)

        if not conn.get('ENGINE'):
            conn['ENGINE'] = 'haystack.backends.simple_backend.SimpleEngine'

    def __getitem__(self, key):
        if not hasattr(self.thread_local, 'connections'):
            self.thread_local.connections = {}
        elif key in self.thread_local.connections:
            return self.thread_local.connections[key]

        self.ensure_defaults(key)
        self.thread_local.connections[key] = load_backend(self.connections_info[key]['ENGINE'])(using=key)
        return self.thread_local.connections[key]

    def reload(self, key):
        if not hasattr(self.thread_local, 'connections'):
            self.thread_local.connections = {}
        try:
            del self.thread_local.connections[key]
        except KeyError:
            pass

        return self.__getitem__(key)

    def all(self):
        return [self[alias] for alias in self.connections_info]


class ConnectionRouter(object):
    def __init__(self):
        self._routers = None

    @property
    def routers(self):
        if self._routers is None:
            default_routers = ['haystack.routers.DefaultRouter']
            router_list = getattr(settings, 'HAYSTACK_ROUTERS', default_routers)
            # in case HAYSTACK_ROUTERS is empty, fallback to default routers
            if not len(router_list):
                router_list = default_routers

            self._routers = []
            for router_path in router_list:
                router_class = load_router(router_path)
                self._routers.append(router_class())
        return self._routers

    def _for_action(self, action, many, **hints):
        conns = []

        for router in self.routers:
            if hasattr(router, action):
                action_callable = getattr(router, action)
                connection_to_use = action_callable(**hints)

                if connection_to_use is not None:
                    if isinstance(connection_to_use, six.string_types):
                        conns.append(connection_to_use)
                    else:
                        conns.extend(connection_to_use)
                    if not many:
                        break

        return conns

    def for_write(self, **hints):
        return self._for_action('for_write', True, **hints)

    def for_read(self, **hints):
        return self._for_action('for_read', False, **hints)[0]


class UnifiedIndex(object):
    # Used to collect all the indexes into a cohesive whole.
    def __init__(self, excluded_indexes=None):
        self._indexes = {}
        self.fields = OrderedDict()
        self._built = False
        self.excluded_indexes = excluded_indexes or []
        self.excluded_indexes_ids = {}
        self.document_field = constants.DOCUMENT_FIELD
        self._fieldnames = {}
        self._facet_fieldnames = {}

    @property
    def indexes(self):
        warnings.warn("'UnifiedIndex.indexes' was deprecated in Haystack v2.3.0. Please use UnifiedIndex.get_indexes().")
        return self._indexes

    def collect_indexes(self):
        indexes = []

        for app_mod in haystack_get_app_modules():
            try:
                search_index_module = importlib.import_module("%s.search_indexes" % app_mod.__name__)
            except ImportError:
                if module_has_submodule(app_mod, 'search_indexes'):
                    raise

                continue

            for item_name, item in inspect.getmembers(search_index_module, inspect.isclass):
                if getattr(item, 'haystack_use_for_indexing', False) and getattr(item, 'get_model', None):
                    # We've got an index. Check if we should be ignoring it.
                    class_path = "%s.search_indexes.%s" % (app_mod.__name__, item_name)

                    if class_path in self.excluded_indexes or self.excluded_indexes_ids.get(item_name) == id(item):
                        self.excluded_indexes_ids[str(item_name)] = id(item)
                        continue

                    indexes.append(item())

        return indexes

    def reset(self):
        self._indexes = {}
        self.fields = OrderedDict()
        self._built = False
        self._fieldnames = {}
        self._facet_fieldnames = {}

    def build(self, indexes=None):
        self.reset()

        if indexes is None:
            indexes = self.collect_indexes()

        for index in indexes:
            model = index.get_model()

            if model in self._indexes:
                raise ImproperlyConfigured(
                    "Model '%s' has more than one 'SearchIndex`` handling it. "
                    "Please exclude either '%s' or '%s' using the 'EXCLUDED_INDEXES' "
                    "setting defined in 'settings.HAYSTACK_CONNECTIONS'." % (
                        model, self._indexes[model], index
                    )
                )

            self._indexes[model] = index
            self.collect_fields(index)

        self._built = True

    def collect_fields(self, index):
        for fieldname, field_object in index.fields.items():
            if field_object.document is True:
                if field_object.index_fieldname != self.document_field:
                    raise SearchFieldError("All 'SearchIndex' classes must use the same '%s' fieldname for the 'document=True' field. Offending index is '%s'." % (self.document_field, index))

            # Stow the index_fieldname so we don't have to get it the hard way again.
            if fieldname in self._fieldnames and field_object.index_fieldname != self._fieldnames[fieldname]:
                # We've already seen this field in the list. Raise an exception if index_fieldname differs.
                raise SearchFieldError("All uses of the '%s' field need to use the same 'index_fieldname' attribute." % fieldname)

            self._fieldnames[fieldname] = field_object.index_fieldname

            # Stow the facet_fieldname so we don't have to look that up either.
            if hasattr(field_object, 'facet_for'):
                if field_object.facet_for:
                    self._facet_fieldnames[field_object.facet_for] = fieldname
                else:
                    self._facet_fieldnames[field_object.instance_name] = fieldname

            # Copy the field in so we've got a unified schema.
            if field_object.index_fieldname not in self.fields:
                self.fields[field_object.index_fieldname] = field_object
                self.fields[field_object.index_fieldname] = copy.copy(field_object)
            else:
                # If the field types are different, we can mostly
                # safely ignore this. The exception is ``MultiValueField``,
                # in which case we'll use it instead, copying over the
                # values.
                if field_object.is_multivalued:
                    old_field = self.fields[field_object.index_fieldname]
                    self.fields[field_object.index_fieldname] = field_object
                    self.fields[field_object.index_fieldname] = copy.copy(field_object)

                    # Switch it so we don't have to dupe the remaining
                    # checks.
                    field_object = old_field

                # We've already got this field in the list. Ensure that
                # what we hand back is a superset of all options that
                # affect the schema.
                if field_object.indexed is True:
                    self.fields[field_object.index_fieldname].indexed = True

                if field_object.stored is True:
                    self.fields[field_object.index_fieldname].stored = True

                if field_object.faceted is True:
                    self.fields[field_object.index_fieldname].faceted = True

                if field_object.use_template is True:
                    self.fields[field_object.index_fieldname].use_template = True

                if field_object.null is True:
                    self.fields[field_object.index_fieldname].null = True

    def get_indexes(self):
        if not self._built:
            self.build()

        return self._indexes

    def get_indexed_models(self):
        # Ensuring a list here since Python3 will give us an iterator
        return list(self.get_indexes().keys())

    def get_index_fieldname(self, field):
        if not self._built:
            self.build()

        return self._fieldnames.get(field) or field

    def get_index(self, model_klass):

        indexes = self.get_indexes()

        if model_klass not in indexes:
            raise NotHandled('The model %s is not registered' % model_klass)

        return indexes[model_klass]

    def get_facet_fieldname(self, field):
        if not self._built:
            self.build()

        for fieldname, field_object in self.fields.items():
            if fieldname != field:
                continue

            if hasattr(field_object, 'facet_for'):
                if field_object.facet_for:
                    return field_object.facet_for
                else:
                    return field_object.instance_name
            else:
                return self._facet_fieldnames.get(field) or field

        return field

    def all_searchfields(self):
        if not self._built:
            self.build()

        return self.fields
