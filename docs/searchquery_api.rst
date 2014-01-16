.. _ref-searchquery-api:

===================
``SearchQuery`` API
===================

.. class:: SearchQuery(using=DEFAULT_ALIAS)

The ``SearchQuery`` class acts as an intermediary between ``SearchQuerySet``'s
abstraction and ``SearchBackend``'s actual search. Given the metadata provided
by ``SearchQuerySet``, ``SearchQuery`` builds the actual query and interacts
with the ``SearchBackend`` on ``SearchQuerySet``'s behalf.

This class must be at least partially implemented on a per-backend basis, as portions
are highly specific to the backend. It usually is bundled with the accompanying
``SearchBackend``.

Most people will **NOT** have to use this class directly. ``SearchQuerySet``
handles all interactions with ``SearchQuery`` objects and provides a nicer
interface to work with.

Should you need advanced/custom behavior, you can supply your version of
``SearchQuery`` that overrides/extends the class in the manner you see fit.
You can either hook it up in a ``BaseEngine`` subclass or ``SearchQuerySet``
objects take a kwarg parameter ``query`` where you can pass in your class.


``SQ`` Objects
==============

For expressing more complex queries, especially involving AND/OR/NOT in
different combinations, you should use ``SQ`` objects. Like
``django.db.models.Q`` objects, ``SQ`` objects can be passed to
``SearchQuerySet.filter`` and use the familiar unary operators (``&``, ``|`` and
``~``) to generate complex parts of the query.

.. warning::

    Any data you pass to ``SQ`` objects is passed along **unescaped**. If
    you don't trust the data you're passing along, you should use
    the ``clean`` method on your ``SearchQuery`` to sanitize the data.

Example::

    from haystack.query import SQ

    # We want "title: Foo AND (tags:bar OR tags:moof)"
    sqs = SearchQuerySet().filter(title='Foo').filter(SQ(tags='bar') | SQ(tags='moof'))

    # To clean user-provided data:
    sqs = SearchQuerySet()
    clean_query = sqs.query.clean(user_query)
    sqs = sqs.filter(SQ(title=clean_query) | SQ(tags=clean_query))

Internally, the ``SearchQuery`` object maintains a tree of ``SQ`` objects. Each
``SQ`` object supports what field it looks up against, what kind of lookup (i.e.
the ``__`` filters), what value it's looking for, if it's a AND/OR/NOT and
tracks any children it may have. The ``SearchQuery.build_query`` method starts
with the root of the tree, building part of the final query at each node until
the full final query is ready for the ``SearchBackend``.


Backend-Specific Methods
========================

When implementing a new backend, the following methods will need to be created:

``build_query_fragment``
~~~~~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.build_query_fragment(self, field, filter_type, value)

Generates a query fragment from a field, filter type and a value.

Must be implemented in backends as this will be highly backend specific.


Inheritable Methods
===================

The following methods have a complete implementation in the base class and
can largely be used unchanged.

``build_query``
~~~~~~~~~~~~~~~

.. method:: SearchQuery.build_query(self)

Interprets the collected query metadata and builds the final query to
be sent to the backend.

``build_params``
~~~~~~~~~~~~~~~~

.. method:: SearchQuery.build_params(self, spelling_query=None)

Generates a list of params to use when searching.

``clean``
~~~~~~~~~

.. method:: SearchQuery.clean(self, query_fragment)

Provides a mechanism for sanitizing user input before presenting the
value to the backend.

A basic (override-able) implementation is provided.

``run``
~~~~~~~

.. method:: SearchQuery.run(self, spelling_query=None, **kwargs)

Builds and executes the query. Returns a list of search results.

Optionally passes along an alternate query for spelling suggestions.

Optionally passes along more kwargs for controlling the search query.

``run_mlt``
~~~~~~~~~~~

.. method:: SearchQuery.run_mlt(self, **kwargs)

Executes the More Like This. Returns a list of search results similar
to the provided document (and optionally query).

``run_raw``
~~~~~~~~~~~

.. method:: SearchQuery.run_raw(self, **kwargs)

Executes a raw query. Returns a list of search results.

``get_count``
~~~~~~~~~~~~~

.. method:: SearchQuery.get_count(self)

Returns the number of results the backend found for the query.

If the query has not been run, this will execute the query and store
the results.

``get_results``
~~~~~~~~~~~~~~~

.. method:: SearchQuery.get_results(self, **kwargs)

Returns the results received from the backend.

If the query has not been run, this will execute the query and store
the results.

``get_facet_counts``
~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.get_facet_counts(self)

Returns the results received from the backend.

If the query has not been run, this will execute the query and store
the results.

``boost_fragment``
~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.boost_fragment(self, boost_word, boost_value)

Generates query fragment for boosting a single word/value pair.

``matching_all_fragment``
~~~~~~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.matching_all_fragment(self)

Generates the query that matches all documents.

``add_filter``
~~~~~~~~~~~~~~

.. method:: SearchQuery.add_filter(self, expression, value, use_not=False, use_or=False)

Narrows the search by requiring certain conditions.

``add_order_by``
~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_order_by(self, field)

Orders the search result by a field.

``clear_order_by``
~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.clear_order_by(self)

Clears out all ordering that has been already added, reverting the
query to relevancy.

``add_model``
~~~~~~~~~~~~~

.. method:: SearchQuery.add_model(self, model)

Restricts the query requiring matches in the given model.

This builds upon previous additions, so you can limit to multiple models
by chaining this method several times.

``set_limits``
~~~~~~~~~~~~~~

.. method:: SearchQuery.set_limits(self, low=None, high=None)

Restricts the query by altering either the start, end or both offsets.

``clear_limits``
~~~~~~~~~~~~~~~~

.. method:: SearchQuery.clear_limits(self)

Clears any existing limits.

``add_boost``
~~~~~~~~~~~~~

.. method:: SearchQuery.add_boost(self, term, boost_value)

Adds a boosted term and the amount to boost it to the query.

``raw_search``
~~~~~~~~~~~~~~

.. method:: SearchQuery.raw_search(self, query_string, **kwargs)

Runs a raw query (no parsing) against the backend.

This method causes the ``SearchQuery`` to ignore the standard query-generating 
facilities, running only what was provided instead.

Note that any kwargs passed along will override anything provided
to the rest of the ``SearchQuerySet``.

``more_like_this``
~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.more_like_this(self, model_instance)

Allows backends with support for "More Like This" to return results
similar to the provided instance.

``add_stats_query``
~~~~~~~~~~~~~~~~~~~
.. method:: SearchQuery.add_stats_query(self,stats_field,stats_facets)

Adds stats and stats_facets queries for the Solr backend.

``add_highlight``
~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_highlight(self)

Adds highlighting to the search results.

``add_within``
~~~~~~~~~~~~~~

.. method:: SearchQuery.add_within(self, field, point_1, point_2):

Adds bounding box parameters to search query.

``add_dwithin``
~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_dwithin(self, field, point, distance):

Adds radius-based parameters to search query.

``add_distance``
~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_distance(self, field, point):

Denotes that results should include distance measurements from the
point passed in.

``add_field_facet``
~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_field_facet(self, field, **options)

Adds a regular facet on a field.

``add_date_facet``
~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_date_facet(self, field, start_date, end_date, gap_by, gap_amount)

Adds a date-based facet on a field.

``add_query_facet``
~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_query_facet(self, field, query)

Adds a query facet on a field.

``add_narrow_query``
~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.add_narrow_query(self, query)

Narrows a search to a subset of all documents per the query.

Generally used in conjunction with faceting.

``set_result_class``
~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuery.set_result_class(self, klass)

Sets the result class to use for results.

Overrides any previous usages. If ``None`` is provided, Haystack will
revert back to the default ``SearchResult`` object.

``using``
~~~~~~~~~

.. method:: SearchQuery.using(self, using=None)

Allows for overriding which connection should be used. This
disables the use of routers when performing the query.

If ``None`` is provided, it has no effect on what backend is used.
