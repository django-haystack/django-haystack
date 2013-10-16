.. _ref-inputtypes:

===========
Input Types
===========

Input types allow you to specify more advanced query behavior. They serve as a
way to alter the query, often in backend-specific ways, without altering your
Python code; as well as enabling use of more advanced features.

Input types currently are only useful with the ``filter/exclude`` methods on
``SearchQuerySet``. Expanding this support to other methods is on the roadmap.


Available Input Types
=====================

Included with Haystack are the following input types:

``Raw``
-------

.. class:: haystack.inputs.Raw

Raw allows you to specify backend-specific query syntax. If Haystack doesn't
provide a way to access special query functionality, you can make use of this
input type to pass it along.

Example::

    # Fielded.
    sqs = SearchQuerySet().filter(author=Raw('daniel OR jones'))

    # Non-fielded.
    # See ``AltParser`` for a better way to construct this.
    sqs = SearchQuerySet().filter(content=Raw('{!dismax qf=author mm=1}haystack'))


``Clean``
---------

.. class:: haystack.inputs.Clean

``Clean`` takes standard user (untrusted) input and sanitizes it. It ensures
that no unintended operators or special characters make it into the query.

This is roughly analogous to Django's ``autoescape`` support.

.. note::

    By default, if you hand a ``SearchQuerySet`` a bare string, it will get
    wrapped in this class.

Example::

    # This becomes "daniel or jones".
    sqs = SearchQuerySet().filter(content=Clean('daniel OR jones'))

    # Things like ``:`` & ``/`` get escaped.
    sqs = SearchQuerySet().filter(url=Clean('http://www.example.com'))

    # Equivalent (automatically wrapped in ``Clean``).
    sqs = SearchQuerySet().filter(url='http://www.example.com')


``Exact``
---------

.. class:: haystack.inputs.Exact

``Exact`` allows for making sure a phrase is exactly matched, unlike the usual
``AND`` lookups, where words may be far apart.

Example::

    sqs = SearchQuerySet().filter(author=Exact('n-gram support'))

    # Equivalent.
    sqs = SearchQuerySet().filter(author__exact='n-gram support')


``Not``
-------

.. class:: haystack.inputs.Not

``Not`` allows negation of the query fragment it wraps. As ``Not`` is a subclass
of ``Clean``, it will also sanitize the query.

This is generally only used internally. Most people prefer to use the
``SearchQuerySet.exclude`` method.

Example::

    sqs = SearchQuerySet().filter(author=Not('daniel'))


``AutoQuery``
-------------

.. class:: haystack.inputs.AutoQuery

``AutoQuery`` takes a more complex user query (that includes simple, standard
query syntax bits) & forms a proper query out of them. It also handles
sanitizing that query using ``Clean`` to ensure the query doesn't break.

``AutoQuery`` accommodates for handling regular words, NOT-ing words &
extracting exact phrases.

Example::

    # Against the main text field with an accidental ":" before "search".
    # Generates a query like ``haystack (NOT whoosh) "fast search"``
    sqs = SearchQuerySet().filter(content=AutoQuery('haystack -whoosh "fast :search"'))

    # Equivalent.
    sqs = SearchQuerySet().auto_query('haystack -whoosh "fast :search"')

    # Fielded.
    sqs = SearchQuerySet().filter(author=AutoQuery('daniel -day -lewis'))


``AltParser``
-------------

.. class:: haystack.inputs.AltParser

``AltParser`` lets you specify that a portion of the query should use a
separate parser in the search engine. This is search-engine-specific, so it may
decrease the portability of your app.

Currently only supported under Solr.

Example::

    # DisMax.
    sqs = SearchQuerySet().filter(content=AltParser('dismax', 'haystack', qf='text', mm=1))

    # Prior to the spatial support, you could do...
    sqs = SearchQuerySet().filter(content=AltParser('dismax', 'haystack', qf='author', mm=1))


Creating Your Own Input Types
=============================

Building your own input type is relatively simple. All input types are simple
classes that provide an ``__init__`` & a ``prepare`` method.

The ``__init__`` may accept any ``args/kwargs``, though the typical use usually
just involves a query string.

The ``prepare`` method lets you alter the query the user provided before it
becomes of the main query. It is lazy, called as late as possible, right before
the final query is built & shipped to the engine.

A full, if somewhat silly, example looks like::

    from haystack.inputs import Clean


    class NoShoutCaps(Clean):
        input_type_name = 'no_shout_caps'
        # This is the default & doesn't need to be specified.
        post_process = True

        def __init__(self, query_string, **kwargs):
            # Stash the original, if you need it.
            self.original = query_string
            super(NoShoutCaps, self).__init__(query_string, **kwargs)

        def prepare(self, query_obj):
            # We need a reference to the current ``SearchQuery`` object this
            # will run against, in case we need backend-specific code.
            query_string = super(NoShoutCaps, self).prepare(query_obj)

            # Take that, capital letters!
            return query_string.lower()
