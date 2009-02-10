==================
SearchQuerySet API
==================

The ``SearchQuerySet`` class is designed to make performing a search and iterating
over its results easy and consistent. For those familiar with Django's ORM
``QuerySet``, much of the ``SearchQuerySet`` API should feel familiar.


Why Follow QuerySet?
====================

A couple reasons to follow (at least in part) the ``QuerySet`` API:

#. Consistency with Django
#. Most Django programmers have experience with the ORM and can use this
   knowledge with ``SearchQuerySet``.

And from a high-level perspective, ``QuerySet`` and ``SearchQuerySet`` do very similar
things: given certain criteria, provide a set of results. Both are powered by
multiple backends, both are abstractions on top of the way a query is performed.


Quick Start
===========

For the impatient::

    from haystack.query import SearchQuerySet
    all_results = SearchQuerySet().all()
    hello_results = SearchQuerySet().filter(content='hello')
    hello_world_results = SearchQuerySet().filter(content='hello world')
    unfriendly_results = SearchQuerySet().exclude(content='hello').filter(content='world')
    recent_results = SearchQuerySet().order_by('-pub_date')[:5]


SearchQuerySet
==============

By default, ``SearchQuerySet`` provide the documented functionality. You can
extend with your own behavior by simply subclassing from ``SearchQuerySet`` and
adding what you need, then using your subclass in place of ``SearchQuerySet``.

Most methods in ``SearchQuerySet`` "chain" in a similar fashion to ``QuerySet``.
Additionally, like ``QuerySet``, ``SearchQuerySet`` is lazy (meaning it evaluates the
query as late as possible). So the following is valid::

    from haystack.query import SearchQuerySet
    results = SearchQuerySet().exclude(content='hello').filter(content='world').order_by('-pub_date').boost('title', 0.5)[10:20]


``SearchQuerySet`` Methods
==========================

Methods That Return A ``SearchQuerySet``
----------------------------------------

``all(self):``
Returns all results for the query.

``filter(self, **kwargs)``
Narrows the search by looking for (and including) certain attributes.

``exclude(self, **kwargs)``
Narrows the search by ensuring certain attributes are not included.

``filter_or(self, **kwargs)``
Narrows the search by ensuring certain attributes are not included.

``order_by(self, field)``

``models(self, *models)``
Accepts an arbitrary number of Model classes to include in the search.

``boost(self, **kwargs)``
Boosts a certain aspect of the query.

``raw_search(self, query_string)``
Passes a raw query directly to the backend.

``load_all(self)``
Efficiently populates the objects in the search results.

``auto_query(self, query_string)``

Performs a best guess constructing the search query.

This method is somewhat naive but works well enough for the simple,
common cases.


Methods That Do Not Return A ``SearchQuerySet``
-----------------------------------------------

``count(self)``
Returns the total number of matching results.

``best_match(self)``
Returns the best/top search result that matches the query.

``latest(self, date_field)``
Returns the most recent search result that matches the query.

``more_like_this(self, model_instance)``
Finds similar results to the object passed in.
