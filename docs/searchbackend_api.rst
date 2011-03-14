.. _ref-searchbackend-api:

=====================
``SearchBackend`` API
=====================

.. class:: SearchBackend(site=None)

The ``SearchBackend`` class handles interaction directly with the backend. The
search query it performs is usually fed to it from a ``SearchQuery`` class that
has been built for that backend.

This class must be at least partially implemented on a per-backend basis and
is usually accompanied by a ``SearchQuery`` class within the same module.

Unless you are writing a new backend, it is unlikely you need to directly
access this class.


Method Reference
================

``update``
----------

.. method:: SearchBackend.update(self, index, iterable)

Updates the backend when given a ``SearchIndex`` and a collection of
documents.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``remove``
----------

.. method:: SearchBackend.remove(self, obj_or_string)

Removes a document/object from the backend. Can be either a model
instance or the identifier (i.e. ``app_name.model_name.id``) in the
event the object no longer exists.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``clear``
---------

.. method:: SearchBackend.clear(self, models=[])

Clears the backend of all documents/objects for a collection of models.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``search``
----------

.. method:: SearchBackend.search(self, query_string, sort_by=None, start_offset=0, end_offset=None, fields='', highlight=False, facets=None, date_facets=None, query_facets=None, narrow_queries=None, spelling_query=None, limit_to_registered_models=None, result_class=None, **kwargs)

Takes a query to search on and returns dictionary.

The query should be a string that is appropriate syntax for the backend.

The returned dictionary should contain the keys 'results' and 'hits'.
The 'results' value should be an iterable of populated ``SearchResult``
objects. The 'hits' should be an integer count of the number of matched
results the search backend found.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``prep_value``
--------------

.. method:: SearchBackend.prep_value(self, value)

Hook to give the backend a chance to prep an attribute value before
sending it to the search engine.

By default, just force it to unicode.

``more_like_this``
------------------

.. method:: SearchBackend.more_like_this(self, model_instance, additional_query_string=None, result_class=None)

Takes a model object and returns results the backend thinks are similar.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``build_schema``
----------------

.. method:: SearchBackend.build_schema(self, fields)

Takes a dictionary of fields and returns schema information.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``build_registered_models_list``
--------------------------------

.. method:: SearchBackend.build_registered_models_list(self)

Builds a list of registered models for searching.

The ``search`` method should use this and the ``django_ct`` field to
narrow the results (unless the user indicates not to). This helps ignore
any results that are not currently registered models and ensures
consistent caching.
