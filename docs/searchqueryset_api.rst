.. _ref-searchqueryset-api:

======================
``SearchQuerySet`` API
======================

.. class:: SearchQuerySet(site=None, query=None)

The ``SearchQuerySet`` class is designed to make performing a search and
iterating over its results easy and consistent. For those familiar with Django's
ORM ``QuerySet``, much of the ``SearchQuerySet`` API should feel familiar.


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
work (e.g. ``filter``, ``exclude``, etc.) to indicate you simply want to
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

``all``
~~~~~~~

.. method:: SearchQuerySet.all(self):

Returns all results for the query. This is largely a no-op (returns an identical
copy) but useful for denoting exactly what behavior is going on.

``none``
~~~~~~~~

.. method:: SearchQuerySet.none(self):

Returns an ``EmptySearchQuerySet`` that behaves like a ``SearchQuerySet`` but
always yields no results.

``filter``
~~~~~~~~~~

.. method:: SearchQuerySet.filter(self, **kwargs)

Filters the search by looking for (and including) certain attributes.

The lookup parameters (``**kwargs``) should follow the `Field lookups`_ below.
If you specify more than one pair, they will be joined in the query according to
the ``HAYSTACK_DEFAULT_OPERATOR`` setting (defaults to ``AND``).

If a string with one or more spaces in it is specified as the value, an exact
match will be performed on that phrase.

.. warning::

    Any data you pass to ``filter`` is passed along **unescaped**. If
    you don't trust the data you're passing along, you should either use
    ``auto_query`` or use the ``clean`` method on your ``SearchQuery`` to
    sanitize the data.

Example::

    SearchQuerySet().filter(content='foo')
    
    SearchQuerySet().filter(content='foo', pub_date__lte=datetime.date(2008, 1, 1))
    
    # Identical to the previous example.
    SearchQuerySet().filter(content='foo').filter(pub_date__lte=datetime.date(2008, 1, 1))
    
    # To escape user data:
    sqs = SearchQuerySet()
    sqs = sqs.filter(title=sqs.query.clean(user_query))

``exclude``
~~~~~~~~~~~

.. method:: SearchQuerySet.exclude(self, **kwargs)

Narrows the search by ensuring certain attributes are not included.

.. warning::

    Any data you pass to ``exclude`` is passed along **unescaped**. If
    you don't trust the data you're passing along, you should either use
    ``auto_query`` or use the ``clean`` method on your ``SearchQuery`` to
    sanitize the data.

Example::

    SearchQuerySet().exclude(content='foo')

``filter_and``
~~~~~~~~~~~~~~

.. method:: SearchQuerySet.filter_and(self, **kwargs)

Narrows the search by looking for (and including) certain attributes. Join
behavior in the query is forced to be ``AND``. Used primarily by the ``filter``
method.

``filter_or``
~~~~~~~~~~~~~

.. method:: SearchQuerySet.filter_or(self, **kwargs)

Narrows the search by looking for (and including) certain attributes. Join
behavior in the query is forced to be ``OR``. Used primarily by the ``filter``
method.

``order_by``
~~~~~~~~~~~~

.. method:: SearchQuerySet.order_by(self, *args)

Alters the order in which the results should appear. Arguments should be strings
that map to the attributes/fields within the index. You may specify multiple
fields by comma separating them::

    SearchQuerySet().filter(content='foo').order_by('author', 'pub_date')

Default behavior is ascending order. To specify descending order, prepend the
string with a ``-``::

    SearchQuerySet().filter(content='foo').order_by('-pub_date')

.. note::

    In general, ordering is locale-specific. Haystack makes no effort to try to
    reconcile differences between characters from different languages. This
    means that accented characters will sort closely with the same character
    and **NOT** necessarily close to the unaccented form of the character.
    
    If you want this kind of behavior, you should override the ``prepare_FOO``
    methods on your ``SearchIndex`` objects to transliterate the characters
    as you see fit.

.. warning::

    **Whoosh only** If you're planning on ordering by an ``IntegerField`` using
    Whoosh, you'll need to adequately zero-pad your numbers in the
    ``prepare_FOO`` method. This is because Whoosh uses UTF-8 string for
    everything, and from the schema, there is no way to know how a field should
    be treated.

``highlight``
~~~~~~~~~~~~~

.. method:: SearchQuerySet.highlight(self)

If supported by the backend, the ``SearchResult`` objects returned will include
a highlighted version of the result::

    sqs = SearchQuerySet().filter(content='foo').highlight()
    result = sqs[0]
    result.highlighted['text'][0] # u'Two computer scientists walk into a bar. The bartender says "<em>Foo</em>!".'

``models``
~~~~~~~~~~

.. method:: SearchQuerySet.models(self, *models)

Accepts an arbitrary number of Model classes to include in the search. This will
narrow the search results to only include results from the models specified.

Example::

    SearchQuerySet().filter(content='foo').models(BlogEntry, Comment)

``result_class``
~~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.result_class(self, klass)

Allows specifying a different class to use for results.

Overrides any previous usages. If ``None`` is provided, Haystack will
revert back to the default ``SearchResult`` object.

Example::

    SearchQuerySet().result_class(CustomResult)

``boost``
~~~~~~~~~

.. method:: SearchQuerySet.boost(self, term, boost_value)

Boosts a certain term of the query. You provide the term to be boosted and the
value is the amount to boost it by. Boost amounts may be either an integer or a
float.

Example::

    SearchQuerySet().filter(content='foo').boost('bar', 1.5)

``facet``
~~~~~~~~~

.. method:: SearchQuerySet.facet(self, field)

Adds faceting to a query for the provided field. You provide the field (from one
of the ``SearchIndex`` classes) you like to facet on.

In the search results you get back, facet counts will be populated in the
``SearchResult`` object. You can access them via the ``facet_counts`` method.

Example::

    # Count document hits for each author within the index.
    SearchQuerySet().filter(content='foo').facet('author')

``date_facet``
~~~~~~~~~~~~~~

.. method:: SearchQuerySet.date_facet(self, field, start_date, end_date, gap_by, gap_amount=1)

Adds faceting to a query for the provided field by date. You provide the field
(from one of the ``SearchIndex`` classes) you like to facet on, a ``start_date``
(either ``datetime.datetime`` or ``datetime.date``), an ``end_date`` and the
amount of time between gaps as ``gap_by`` (one of ``'year'``, ``'month'``,
``'day'``, ``'hour'``, ``'minute'`` or ``'second'``).

You can also optionally provide a ``gap_amount`` to specify a different
increment than ``1``. For example, specifying gaps by week (every seven days)
would would be ``gap_by='day', gap_amount=7``).

In the search results you get back, facet counts will be populated in the
``SearchResult`` object. You can access them via the ``facet_counts`` method.

Example::

    # Count document hits for each day between 2009-06-07 to 2009-07-07 within the index.
    SearchQuerySet().filter(content='foo').date_facet('pub_date', start_date=datetime.date(2009, 6, 7), end_date=datetime.date(2009, 7, 7), gap_by='day')

``query_facet``
~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.query_facet(self, field, query)

Adds faceting to a query for the provided field with a custom query. You provide
the field (from one of the ``SearchIndex`` classes) you like to facet on and the
backend-specific query (as a string) you'd like to execute.

Please note that this is **NOT** portable between backends. The syntax is entirely
dependent on the backend. No validation/cleansing is performed and it is up to
the developer to ensure the query's syntax is correct.

In the search results you get back, facet counts will be populated in the
``SearchResult`` object. You can access them via the ``facet_counts`` method.

Example::

    # Count document hits for authors that start with 'jo' within the index.
    SearchQuerySet().filter(content='foo').query_facet('author', 'jo*')

``narrow``
~~~~~~~~~~

.. method:: SearchQuerySet.narrow(self, query)

Pulls a subset of documents from the search engine to search within. This is
for advanced usage, especially useful when faceting.

Example::

    # Search, from recipes containing 'blend', for recipes containing 'banana'.
    SearchQuerySet().narrow('blend').filter(content='banana')
    
    # Using a fielded search where the recipe's title contains 'smoothie', find all recipes published before 2009.
    SearchQuerySet().narrow('title:smoothie').filter(pub_date__lte=datetime.datetime(2009, 1, 1))

By using ``narrow``, you can create drill-down interfaces for faceting by
applying ``narrow`` calls for each facet that gets selected.

This method is different from ``SearchQuerySet.filter()`` in that it does not
affect the query sent to the engine. It pre-limits the document set being
searched. Generally speaking, if you're in doubt of whether to use
``filter`` or ``narrow``, use ``filter``.

.. note::

    This method is, generally speaking, not necessarily portable between
    backends. The syntax is entirely dependent on the backend, though most
    backends have a similar syntax for basic fielded queries. No
    validation/cleansing is performed and it is up to the developer to ensure
    the query's syntax is correct.

``raw_search``
~~~~~~~~~~~~~~

.. method:: SearchQuerySet.raw_search(self, query_string, **kwargs)

Passes a raw query directly to the backend. This is for advanced usage, where
the desired query can not be expressed via ``SearchQuerySet``.

.. warning::

    Unlike many of the other methods on ``SearchQuerySet``, this method does
    not chain by default (depends on the backend). Any other attributes on the
    ``SearchQuerySet`` are ignored and only the provided query is run.

Example::

    # In the case of Solr... (this example could be expressed with SearchQuerySet)
    SearchQuerySet().raw_search('django_ct:blog.blogentry "However, it is"')

Please note that this is **NOT** portable between backends. The syntax is entirely
dependent on the backend. No validation/cleansing is performed and it is up to
the developer to ensure the query's syntax is correct.

Further, the use of ``**kwargs`` are completely undocumented intentionally. If
a third-party backend can implement special features beyond what's present, it
should use those ``**kwargs`` for passing that information. Developers should
be careful to make sure there are no conflicts with the backend's ``search``
method, as that is called directly.

``load_all``
~~~~~~~~~~~~

.. method:: SearchQuerySet.load_all(self)

Efficiently populates the objects in the search results. Without using this
method, DB lookups are done on a per-object basis, resulting in many individual
trips to the database. If ``load_all`` is used, the ``SearchQuerySet`` will
group similar objects into a single query, resulting in only as many queries as
there are different object types returned.

Example::

    SearchQuerySet().filter(content='foo').load_all()

``load_all_queryset``
~~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.load_all_queryset(self, model_class, queryset)

Deprecated for removal before Haystack 1.0-final.

Please see the docs on ``RelatedSearchQuerySet``.

``auto_query``
~~~~~~~~~~~~~~

.. method:: SearchQuerySet.auto_query(self, query_string)

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

``autocomplete``
~~~~~~~~~~~~~~~~

A shortcut method to perform an autocomplete search.

Must be run against fields that are either ``NgramField`` or
``EdgeNgramField``.

Example::

    SearchQuerySet().autocomplete(title_autocomplete='gol')

``more_like_this``
~~~~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.more_like_this(self, model_instance)

Finds similar results to the object passed in.

You should pass in an instance of a model (for example, one fetched via a
``get`` in Django's ORM). This will execute a query on the backend that searches
for similar results. The instance you pass in should be an indexed object.
Previously called methods will have an effect on the provided results.

It will evaluate its own backend-specific query and populate the
`SearchQuerySet`` in the same manner as other methods.

Example::

    entry = Entry.objects.get(slug='haystack-one-oh-released')
    mlt = SearchQuerySet().more_like_this(entry)
    mlt.count() # 5
    mlt[0].object.title # "Haystack Beta 1 Released"
    
    # ...or...
    mlt = SearchQuerySet().filter(public=True).exclude(pub_date__lte=datetime.date(2009, 7, 21)).more_like_this(entry)
    mlt.count() # 2
    mlt[0].object.title # "Haystack Beta 1 Released"


Methods That Do Not Return A ``SearchQuerySet``
-----------------------------------------------

``count``
~~~~~~~~~

.. method:: SearchQuerySet.count(self)

Returns the total number of matching results.

This returns an integer count of the total number of results the search backend
found that matched. This method causes the query to evaluate and run the search.

Example::

    SearchQuerySet().filter(content='foo').count()

``best_match``
~~~~~~~~~~~~~~

.. method:: SearchQuerySet.best_match(self)

Returns the best/top search result that matches the query.

This method causes the query to evaluate and run the search. This method returns
a ``SearchResult`` object that is the best match the search backend found::

    foo = SearchQuerySet().filter(content='foo').best_match()
    foo.id # Something like 5.
    
    # Identical to:
    foo = SearchQuerySet().filter(content='foo')[0]

``latest``
~~~~~~~~~~

.. method:: SearchQuerySet.latest(self, date_field)

Returns the most recent search result that matches the query.

This method causes the query to evaluate and run the search. This method returns
a ``SearchResult`` object that is the most recent match the search backend
found::

    foo = SearchQuerySet().filter(content='foo').latest('pub_date')
    foo.id # Something like 3.
    
    # Identical to:
    foo = SearchQuerySet().filter(content='foo').order_by('-pub_date')[0]

``facet_counts``
~~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.facet_counts(self)

Returns the facet counts found by the query. This will cause the query to
execute and should generally be used when presenting the data (template-level).

You receive back a dictionary with three keys: ``fields``, ``dates`` and
``queries``. Each contains the facet counts for whatever facets you specified
within your ``SearchQuerySet``.

.. note::

    The resulting dictionary may change before 1.0 release. It's fairly
    backend-specific at the time of writing. Standardizing is waiting on
    implementing other backends that support faceting and ensuring that the
    results presented will meet their needs as well.

Example::

    # Count document hits for each author.
    sqs = SearchQuerySet().filter(content='foo').facet('author')
    
    sqs.facet_counts()
    # Gives the following response:
    # {
    #     'dates': {},
    #     'fields': {
    #         'author': [
    #             ('john', 4),
    #             ('daniel', 2),
    #             ('sally', 1),
    #             ('terry', 1),
    #         ],
    #     },
    #     'queries': {}
    # }

``spelling_suggestion``
~~~~~~~~~~~~~~~~~~~~~~~

.. method:: SearchQuerySet.spelling_suggestion(self, preferred_query=None)

Returns the spelling suggestion found by the query.

To work, you must set ``settings.HAYSTACK_INCLUDE_SPELLING`` (see
:doc:`settings`) to ``True``. Otherwise, ``None`` will be returned.

This method causes the query to evaluate and run the search if it hasn't already
run. Search results will be populated as normal but with an additional spelling
suggestion. Note that this does *NOT* run the revised query, only suggests
improvements.

If provided, the optional argument to this method lets you specify an alternate
query for the spelling suggestion to be run on. This is useful for passing along
a raw user-provided query, especially when there are many methods chained on the
``SearchQuerySet``.

Example::

    sqs = SearchQuerySet().auto_query('mor exmples')
    sqs.spelling_suggestion() # u'more examples'
    
    # ...or...
    suggestion = SearchQuerySet().spelling_suggestion('moar exmples')
    suggestion # u'more examples'


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
* range

These options are similar in function to the way Django's lookup types work.
The actual behavior of these lookups is backend-specific.

.. warning::

    The ``startswith`` filter is strongly affected by the other ways the engine
    parses data, especially in regards to stemming (see :doc:`glossary`). This
    can mean that if the query ends in a vowel or a plural form, it may get
    stemmed before being evaluated.
    
    This is both backend-specific and yet fairly consistent between engines,
    and may be the cause of sometimes unexpected results.

Example::

    SearchQuerySet().filter(content='foo')
    
    # Identical to:
    SearchQuerySet().filter(content__exact='foo')
    
    # Other usages look like:
    SearchQuerySet().filter(pub_date__gte=datetime.date(2008, 1, 1), pub_date__lt=datetime.date(2009, 1, 1))
    SearchQuerySet().filter(author__in=['daniel', 'john', 'jane'])
    SearchQuerySet().filter(view_count__range=[3, 5])


``EmptySearchQuerySet``
=======================

Also included in Haystack is an ``EmptySearchQuerySet`` class. It behaves just
like ``SearchQuerySet`` but will always return zero results. This is useful for
places where you want no query to occur or results to be returned.


``RelatedSearchQuerySet``
=========================

Sometimes you need to filter results based on relations in the database that are
not present in the search index or are difficult to express that way. To this
end, ``RelatedSearchQuerySet`` allows you to post-process the search results by
calling ``load_all_queryset``.

.. warning::

    ``RelatedSearchQuerySet`` can have negative performance implications.
    Because results are excluded based on the database after the search query
    has been run, you can't guarantee offsets within the cache. Therefore, the
    entire cache that appears before the offset you request must be filled in
    order to produce consistent results. On large result sets and at higher
    slices, this can take time.
    
    This is the old behavior of ``SearchQuerySet``, so performance is no worse
    than the early days of Haystack.

It supports all other methods that the standard ``SearchQuerySet`` does, with
the addition of the ``load_all_queryset`` method and paying attention to the
``load_all_queryset`` method of ``SearchIndex`` objects when populating the
cache.

``load_all_queryset``
---------------------

.. method:: RelatedSearchQuerySet.load_all_queryset(self, model_class, queryset)

Allows for specifying a custom ``QuerySet`` that changes how ``load_all`` will
fetch records for the provided model. This is useful for post-processing the
results from the query, enabling things like adding ``select_related`` or
filtering certain data.

Example::

    sqs = RelatedSearchQuerySet().filter(content='foo').load_all()
    # For the Entry model, we want to include related models directly associated
    # with the Entry to save on DB queries.
    sqs = sqs.load_all_queryset(Entry, Entry.objects.all().select_related(depth=1))

This method chains indefinitely, so you can specify ``QuerySets`` for as many
models as you wish, one per model. The ``SearchQuerySet`` appends on a call to
``in_bulk``, so be sure that the ``QuerySet`` you provide can accommodate this
and that the ids passed to ``in_bulk`` will map to the model in question.

If you need to do this frequently and have one ``QuerySet`` you'd like to apply
everywhere, you can specify this at the ``SearchIndex`` level using the
``load_all_queryset`` method. See :doc:`searchindex_api` for usage.
