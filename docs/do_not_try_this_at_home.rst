.. _ref-advanced-topics:

===============
Advanced Topics
===============

Swapping Backends
=================

As part of the backend loading infrastructure, you can load more than one
search backend at a time or dynamically swap out the backend being used. The
following code demonstrates loading the ``simple`` backend::

    import haystack
    simple_backend = haystack.load_backend('simple')

If no argument is provided, Haystack will load whatever is in the
``HAYSTACK_SEARCH_ENGINE`` setting. Otherwise, any of the following strings
will load their respective backend.

    * solr
    * xapian
    * whoosh
    * simple
    * dummy

You can also provide the "short" portion of the name (before the ``_backend``)
of a custom backend. Haystack will attempt to load that backend instead from
your ``PYTHONPATH``.
