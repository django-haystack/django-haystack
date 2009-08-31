===================
``SearchQuery`` API
===================

The ``SearchQuery`` class acts as an intermediary between ``SearchQuerySet``'s
abstraction and ``SearchBackend``'s actual search. Given the metadata provided
by ``SearchQuerySet``, ``SearchQuery`` build the actual query and interacts
with the ``SearchBackend`` on ``SearchQuerySet``'s behalf.

This class must be at least partially implemented on a per-backend basis, as portions
are highly specific to the backend. It usually is bundled with the accompanying
``SearchBackend``.

Most people will **NOT** have to use this class directly. ``SearchQuerySet``
handles all interactions with ``SearchQuery`` objects and provides a nicer
interface to work with.

Should you need advanced/custom behavior, you can supply your version of
``SearchQuery`` that overrides/extends the class in the manner you see fit.
``SearchQuerySet`` objects take a kwarg parameter ``query`` where you can pass
in your class.


Query Filters
=============

The ``SearchQuery`` object maintains a list of ``QueryFilter`` objects. Each filter
object supports what field it looks up against, what kind of lookup (i.e. 
the __'s), what value it's looking for and if it's a AND/OR/NOT. The
``SearchQuery`` object's "build_query" method should then iterate over that list and 
convert that to a valid query for the search backend.


Backend-Specific Methods
========================

When implementing a new backend, the following methods will need to be created:

``run(self, spelling_query=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Builds and executes the query. Returns a list of search results.

Optionally passes along an alternate query for spelling suggestions.

``build_query(self)``
~~~~~~~~~~~~~~~~~~~~~

Interprets the collected query metadata and builds the final query to
be sent to the backend.

This method MUST be implemented by each backend, as it will be highly
specific to each one.

``run_mlt(self)``
~~~~~~~~~~~~~~~~~

Executes the More Like This. Returns a list of search results similar
to the provided document (and optionally query).


Inheritable Methods
===================

The following methods have a complete implementation in the base class and
can largely be used unchanged.

``clean(self, query_fragment)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a mechanism for sanitizing user input before presenting the
value to the backend.

A basic (override-able) implementation is provided.

``get_count(self)``
~~~~~~~~~~~~~~~~~~~

Returns the number of results the backend found for the query.

If the query has not been run, this will execute the query and store
the results.

``get_results(self)``
~~~~~~~~~~~~~~~~~~~~~

Returns the results received from the backend.

If the query has not been run, this will execute the query and store
the results.

``get_facet_counts(self)``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the results received from the backend.

If the query has not been run, this will execute the query and store
the results.

``add_filter(self, expression, value, use_not=False, use_or=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Narrows the search by requiring certain conditions.

``add_order_by(self, field)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Orders the search result by a field.

``clear_order_by(self)``
~~~~~~~~~~~~~~~~~~~~~~~~

Clears out all ordering that has been already added, reverting the
query to relevancy.

``add_model(self, model)``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Restricts the query requiring matches in the given model.

This builds upon previous additions, so you can limit to multiple models
by chaining this method several times.

``set_limits(self, low=None, high=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restricts the query by altering either the start, end or both offsets.

``clear_limits(self)``
~~~~~~~~~~~~~~~~~~~~~~

Clears any existing limits.

``add_boost(self, term, boost_value)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adds a boosted term and the amount to boost it to the query.

``raw_search(self, query_string, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs a raw query (no parsing) against the backend.

This method does not affect the internal state of the ``SearchQuery`` used
to build queries. It does however populate the results/hit_count.

``more_like_this(self, model_instance)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Allows backends with support for "More Like This" to return results
similar to the provided instance.

``add_highlight(self)``
~~~~~~~~~~~~~~~~~~~~~~~

Adds highlighting to the search results.

``add_field_facet(self, field)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adds a regular facet on a field.

``add_date_facet(self, field, start_date, end_date, gap_by, gap_amount)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adds a date-based facet on a field.

``add_query_facet(self, field, query)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adds a query facet on a field.

``add_narrow_query(self, query)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adds a existing facet on a field.
