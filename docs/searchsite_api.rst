==================
``SearchSite`` API
==================

The ``SearchSite`` provides a way to collect the ``SearchIndexes`` that are
relevant to the current site, much like ``ModelAdmins`` in the ``admin`` app.

This allows you to register indexes on models you don't control (reusable
apps, ``django.contrib``, etc.) as well as customize on a per-site basis what
indexes should be available (different indexes for different sites, same
codebase).

A ``SearchSite`` instance should be instantiated in your URLconf, since all
models will have been loaded by that point.


Autodiscovery
=============

Since the common use case is to simply grab everything that is indexed for
search, there is an autodiscovery mechanism which will pull in and register
all indexes it finds within your project. To enable this, place the following
inside your ``ROOT_URLCONF``::

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

``register(self, model, index_class=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Registers a model with the site.

The model should be a Model class, not instances.

If no custom index is provided, a generic SearchIndex will be applied
to the model.

``unregister(self, model)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unregisters a model's corresponding index from the site.

``get_index(self, model)``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides the index that's registered for a particular model.

``get_indexes(self)``
~~~~~~~~~~~~~~~~~~~~~

Provides a dictionary of all indexes that're being used.

``get_indexed_models(self)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a list of all models being indexed.

``build_unified_schema(self)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Builds a list of all fields appearing in any of the SearchIndexes registered
with a site.

This is useful when building a schema for an engine. A list of dictionaries
is returned, with each dictionary being a field and the attributes about the
field. Valid keys are 'field', 'type', 'indexed' and 'multi_valued'.

With no arguments, it will pull in the main site to discover the available
SearchIndexes.

``update_object(self, instance)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Updates the instance's data in the index.

A shortcut for updating on the instance's index. Errors from `get_index`
and `update_object` will be allowed to propogate.

``remove_object(self, instance)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Removes the instance's data in the index.

A shortcut for removing on the instance's index. Errors from `get_index`
and `remove_object` will be allowed to propogate.
