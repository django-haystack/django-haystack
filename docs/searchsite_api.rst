.. _ref-searchsite-api:

==================
``SearchSite`` API
==================

.. class:: SearchSite

The ``SearchSite`` provides a way to collect the ``SearchIndexes`` that are
relevant to the current site, much like ``ModelAdmins`` in the ``admin`` app.

This allows you to register indexes on models you don't control (reusable
apps, ``django.contrib``, etc.) as well as customize on a per-site basis what
indexes should be available (different indexes for different sites, same
codebase).

A ``SearchSite`` instance(s) should be configured within a configuration file, which gets specified in your settings file as ``HAYSTACK_SITECONF``. An example of this setting might be ``myproject.search_sites``.

.. warning::

    For a long time before the 1.0 release of Haystack, the convention was to
    place this configuration within your URLconf. This is no longer recommended
    as it can cause issues in certain production setups (Django 1.1+/mod_wsgi
    for example).


Autodiscovery
=============

Since the common use case is to simply grab everything that is indexed for
search, there is an autodiscovery mechanism which will pull in and register
all indexes it finds within your project. To enable this, place the following
code inside the file you specified as your ``HAYSTACK_SITECONF``::

    import haystack
    haystack.autodiscover()

This will fully flesh-out the default ``SearchSite`` (at
``haystack.sites.site``) for use. Since this site is used by default throughout
Haystack, very little (if any) additional configuration will be needed.


Usage
=====

If you need to narrow the indexes that get registered, you will need to
manipulate a ``SearchSite``. There are two ways to go about this, via either
``register`` or ``unregister``.

If you want most of the indexes but want to forgo a specific one(s), you can
setup the main ``site`` via ``autodiscover`` then simply unregister the one(s)
you don't want.::

    import haystack
    haystack.autodiscover()
    
    # Unregister the Rating index.
    from ratings.models import Rating
    haystack.sites.site.unregister(Rating)

Alternatively, you can manually register only the indexes you want.::

    from haystack import site
    from ratings.models import Rating
    from ratings.search_indexes import RatingIndex
    
    site.register(Rating, RatingIndex)


Method Reference
================

``register``
~~~~~~~~~~~~

.. method:: SearchSite.register(self, model, index_class=None)

Registers a model with the site.

The model should be a Model class, not instances.

If no custom index is provided, a generic SearchIndex will be applied
to the model.

``unregister``
~~~~~~~~~~~~~~

.. method:: SearchSite.unregister(self, model)

Unregisters a model's corresponding index from the site.

``get_index``
~~~~~~~~~~~~~

.. method:: SearchSite.get_index(self, model)

Provides the index that's registered for a particular model.

``get_indexes``
~~~~~~~~~~~~~~~

.. method:: SearchSite.get_indexes(self)

Provides a dictionary of all indexes that're being used.

``get_indexed_models``
~~~~~~~~~~~~~~~~~~~~~~

.. method:: SearchSite.get_indexed_models(self)

Provides a list of all models being indexed.

``all_searchfields``
~~~~~~~~~~~~~~~~~~~~

.. method:: SearchSite.all_searchfields(self)

Builds a dictionary of all fields appearing in any of the `SearchIndex`
instances registered with a site.

This is useful when building a schema for an engine. A dictionary is
returned, with each key being a fieldname (or index_fieldname) and the
value being the `SearchField` class assigned to it.

``update_object``
~~~~~~~~~~~~~~~~~

.. method:: SearchSite.update_object(self, instance)

Updates the instance's data in the index.

A shortcut for updating on the instance's index. Errors from `get_index`
and `update_object` will be allowed to propogate.

``remove_object``
~~~~~~~~~~~~~~~~~

.. method:: SearchSite.remove_object(self, instance)

Removes the instance's data in the index.

A shortcut for removing on the instance's index. Errors from `get_index`
and `remove_object` will be allowed to propogate.
