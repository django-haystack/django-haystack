======================
``SearchQuerySet`` API
======================

The ``SearchQuerySet`` class is designed to make performing a search and iterating
over its results easy and consistent. For those familiar with Django's ORM
``QuerySet``, much of the ``SearchQuerySet`` API should feel familiar.


Why Follow ``QuerySet``?
========================

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


``SearchQuerySet``
==================

By default, ``SearchQuerySet`` provide the documented functionality. You can
extend with your own behavior by simply subclassing from ``SearchQuerySet`` and
adding what you need, then using your subclass in place of ``SearchQuerySet``.

Most methods in ``SearchQuerySet`` "chain" in a similar fashion to ``QuerySet``.
Additionally, like ``QuerySet``, ``SearchQuerySet`` is lazy (meaning it evaluates the
query as late as possible). So the following is valid::

    from haystack.query import SearchQuerySet
    results = SearchQuerySet().exclude(content='hello').filter(content='world').order_by('-pub_date').boost('title', 0.5)[10:20]


The ``content`` Shortcut
========================

Searching your document fields is a very common activity. To help mitigate
possible differences in ``SearchField`` names (and to help the backends deal
with search queries that inspect the main corpus), there is a special field
called ``content``. You may use this in any place that other fields names would
work (e.g. `` filter``, ``exclude``, etc.) to indicate you simply want to
search the main documents.

For example::

    from haystack.query import SearchQuerySet
    
    # This searches whatever fields were marked ``document=True``.
    results = SearchQuerySet().exclude(content='hello')

This special pseudo-field works best with the ``exact`` lookup and may yield
strange or unexpected results with the other lookups.


``SearchQuerySet`` Methods
==========================

The primary interface to search in Haystack is through the ``SearchQuerySet``
object. It provides a clean, programmatic, portable API to the search backend.
Many aspects are also "chainable", meaning you can call methods one after another, each
applying their changes to the previous ``SearchQuerySet`` and further narrowing
the search.

All ``SearchQuerySet`` objects implement a list-like interface, meaning you can
perform actions like getting the length of the results, accessing a result at an
offset or even slicing the result list.


Methods That Return A ``SearchQuerySet``
----------------------------------------

``all(self):``
~~~~~~~~~~~~~~

Returns all results for the query. This is largely a no-op (returns an identical
copy) but useful for denoting exactly what behavior is going on.

``filter(self, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Narrows the search by looking for (and including) certain attributes.

The lookup parameters (``**kwargs``) should follow the `Field lookups`_ below.
If you specify more than one pair, they will be joined in the query according to
the ``HAYSTACK_DEFAULT_OPERATOR`` setting (defaults to ``AND``).

If a string with one or more spaces in it is specified as the value, an exact
match will be performed on that phrase.

Example::

    SearchQuerySet().filter(content='foo')
    
    SearchQuerySet().filter(content='foo', pub_date__lte=datetime.date(2008, 1, 1))
    
    # Identical to the previous example.
    SearchQuerySet().filter(content='foo').filter(pub_date__lte=datetime.date(2008, 1, 1))

``exclude(self, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Narrows the search by ensuring certain attributes are not included.

Example::

    SearchQuerySet().exclude(content='foo')

``filter_and(self, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Narrows the search by looking for (and including) certain attributes. Join
behavior in the query is forced to be ``AND``. Used primarily by the ``filter``
method.

``filter_or(self, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Narrows the search by looking for (and including) certain attributes. Join
behavior in the query is forced to be ``OR``. Used primarily by the ``filter``
method.

``order_by(self, *args)``
~~~~~~~~~~~~~~~~~~~~~~~~~

Alters the order in which the results should appear. Arguments should be strings
that map to the attributes/fields within the index. You may specify multiple
fields by comma separating them::

    SearchQuerySet().filter(content='foo').order_by('author', 'pub_date')

Default behavior is ascending order. To specify descending order, prepend the
string with a ``-``::

    SearchQuerySet().filter(content='foo').order_by('-pub_date')

``highlight(self)``
~~~~~~~~~~~~~~~~~~~

If supported by the backend, the ``SearchResult`` objects returned will include
a highlighted version of the result::

    SearchQuerySet().filter(content='foo').highlight()

``models(self, *models)``
~~~~~~~~~~~~~~~~~~~~~~~~~

Accepts an arbitrary number of Model classes to include in the search. This will
narrow the search results to only include results from the models specified.

Example::

    SearchQuerySet().filter(content='foo').models(BlogEntry, Comment)

``boost(self, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~

Boosts a certain term of the query. You should provide pairs, where the
parameter is the term to be boosted and the value is the amount to boost it by.
Boost amounts may be either an integer or a float.

Example::

    SearchQuerySet().filter(content='foo').boost(bar=1.5)

``facet(self, field)``
~~~~~~~~~~~~~~~~~~~~~~

Implemented. Documentation coming soon.

``date_facet(self, field, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implemented. Documentation coming soon.

``query_facet(self, field, query)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implemented. Documentation coming soon.

``narrow(self, query)``
~~~~~~~~~~~~~~~~~~~~~~~

Implemented. Documentation coming soon.

``raw_search(self, query_string)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes a raw query directly to the backend. This is for advanced usage, where
the desired query can not be expressed via ``SearchQuerySet``.

Example::

    # In the case of Solr... (this example could be expressed with SearchQuerySet)
    SearchQuerySet().raw_search('django_ct_s:blog.blogentry "However, it is"')

Please note that this is **NOT** portable between backends. The syntax is entirely
dependent on the backend. No validation/cleansing is performed and it is up to
the developer to ensure the query's syntax is correct.

``load_all(self)``
~~~~~~~~~~~~~~~~~~

Efficiently populates the objects in the search results. Without using this
method, DB lookups are done on a per-object basis, resulting in many individual
trips to the database. If ``load_all`` is used, the ``SearchQuerySet`` will
group similar objects into a single query, resulting in only as many queries as
there are different object types returned.

Example::

    SearchQuerySet().filter(content='foo').load_all()

``auto_query(self, query_string)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Performs a best guess constructing the search query.

This method is intended for common use directly with a user's query. It is a
shortcut to the other API methods that follows generally established search
syntax without requiring each developer to implement their own parser.

It handles exact matches (specified with single or double quotes), negation (
using a ``-`` immediately before the term) and joining remaining terms with the
operator specified in ``HAYSTACK_DEFAULT_OPERATOR``.

Example::

    SearchQuerySet().auto_query('goldfish "old one eye" -tank')
    
    # ... is identical to...
    SearchQuerySet().filter(content='old one eye').filter(content='goldfish').exclude(content='tank')

This method is somewhat naive but works well enough for simple, common cases.


Methods That Do Not Return A ``SearchQuerySet``
-----------------------------------------------

``count(self)``
~~~~~~~~~~~~~~~

Returns the total number of matching results.

This returns an integer count of the total number of results the search backend
found that matched. This method causes the query to evaluate and run the search.

Example::

    SearchQuerySet().filter(content='foo').count()

``best_match(self)``
~~~~~~~~~~~~~~~~~~~~

Returns the best/top search result that matches the query.

This method causes the query to evaluate and run the search. This method returns
a ``SearchResult`` object that is the best match the search backend found::

    foo = SearchQuerySet().filter(content='foo').best_match()
    foo.id # Something like 5.
    
    # Identical to:
    foo = SearchQuerySet().filter(content='foo')[0]

``latest(self, date_field)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the most recent search result that matches the query.

This method causes the query to evaluate and run the search. This method returns
a ``SearchResult`` object that is the most recent match the search backend
found::

    foo = SearchQuerySet().filter(content='foo').latest('pub_date')
    foo.id # Something like 3.
    
    # Identical to:
    foo = SearchQuerySet().filter(content='foo').order_by('-pub_date')[0]

``more_like_this(self, model_instance)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finds similar results to the object passed in.

You should pass in an instance of a model (for example, one fetched via a
``get`` in Django's ORM). This will execute a query on the backend that searches
for similar results. The instance you pass in should be an indexed object.
This method does not actually effect the existing ``SearchQuerySet`` but will
ignore any existing constraints.

It will evaluate its own backend-specific query and return a dictionary with two
keys: ``results`` (which will be a list of ``SearchResult`` objects) and
``hits`` (an integer count of the total number of similar results).

The number of results returned will be backend/configuration specific.

Example::

    entry = Entry.objects.get(slug='haystack-one-oh-released')
    mlt = SearchQuerySet().more_like_this(entry)
    mlt['hits'] # 5
    mlt['results'][0].object.title # "Haystack Beta 1 Released"

``facet_counts(self)``
~~~~~~~~~~~~~~~~~~~~~~

Implemented. Documentation coming soon.

.. _field-lookups:

Field Lookups
-------------

The following lookup types are supported:

* exact
* gt
* gte
* lt
* lte
* in
* startswith

These options are similar in function to the way Django's lookup types work.
The actual behavior of these lookups is backend-specific.

Example::

    SearchQuerySet().filter(content='foo')
    
    # Identical to:
    SearchQuerySet().filter(content__exact='foo')
    
    # Other usages look like:
    SearchQuerySet().filter(pub_date__gte=datetime.date(2008, 1, 1), pub_date__lt=datetime.date(2009, 1, 1))
    SearchQuerySet().filter(author__in=['daniel', 'john', 'jane'])
