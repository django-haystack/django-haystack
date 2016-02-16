.. _ref-settings:

=================
Haystack Settings
=================

As a way to extend/change the default behavior within Haystack, there are
several settings you can alter within your ``settings.py``. This is a
comprehensive list of the settings Haystack recognizes.


``HAYSTACK_DEFAULT_OPERATOR``
=============================

**Optional**

This setting controls what the default behavior for chaining ``SearchQuerySet``
filters together is.

Valid options are::

    HAYSTACK_DEFAULT_OPERATOR = 'AND'
    HAYSTACK_DEFAULT_OPERATOR = 'OR'

Defaults to ``AND``.


``HAYSTACK_CONNECTIONS``
========================

**Required**

This setting controls which backends should be available. It should be a
dictionary of dictionaries resembling the following (complete) example::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:9001/solr/default',
            'TIMEOUT': 60 * 5,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'EXCLUDED_INDEXES': ['thirdpartyapp.search_indexes.BarIndex'],
        },
        'autocomplete': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': '/home/search/whoosh_index',
            'STORAGE': 'file',
            'POST_LIMIT': 128 * 1024 * 1024,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'EXCLUDED_INDEXES': ['thirdpartyapp.search_indexes.BarIndex'],
        },
        'slave': {
            'ENGINE': 'xapian_backend.XapianEngine',
            'PATH': '/home/search/xapian_index',
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'EXCLUDED_INDEXES': ['thirdpartyapp.search_indexes.BarIndex'],
        },
        'db': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
            'EXCLUDED_INDEXES': ['thirdpartyapp.search_indexes.BarIndex'],
        }
    }

No default for this setting is provided.

The main keys (``default`` & friends) are identifiers for your application.
You can use them any place the API exposes ``using`` as a method or kwarg.

There must always be at least a ``default`` key within this setting.

The ``ENGINE`` option is required for all backends & should point to the
``BaseEngine`` subclass for the backend.

Additionally, each backend may have additional options it requires:

* Solr

  * ``URL`` - The URL to the Solr core.

* Whoosh

  * ``PATH`` - The filesystem path to where the index data is located.

* Xapian

  * ``PATH`` - The filesystem path to where the index data is located.

The following options are optional:

* ``INCLUDE_SPELLING`` - Include spelling suggestions. Default is ``False``
* ``BATCH_SIZE`` - How many records should be updated at once via the management
  commands. Default is ``1000``.
* ``TIMEOUT`` - (Solr and ElasticSearch) How long to wait (in seconds) before
  the connection times out. Default is ``10``.
* ``STORAGE`` - (Whoosh-only) Which storage engine to use. Accepts ``file`` or
  ``ram``. Default is ``file``.
* ``POST_LIMIT`` - (Whoosh-only) How large the file sizes can be. Default is
  ``128 * 1024 * 1024``.
* ``FLAGS`` - (Xapian-only) A list of flags to use when querying the index.
* ``EXCLUDED_INDEXES`` - A list of strings (as Python import paths) to indexes
  you do **NOT** want included. Useful for omitting third-party things you
  don't want indexed or for when you want to replace an index.
* ``KWARGS`` - (Solr and ElasticSearch) Any additional keyword arguments that
  should be passed on to the underlying client library.


``HAYSTACK_ROUTERS``
====================

**Optional**

This setting controls how routing is performed to allow different backends to
handle updates/deletes/reads.

An example::

    HAYSTACK_ROUTERS = ['search_routers.MasterSlaveRouter', 'haystack.routers.DefaultRouter']

Defaults to ``['haystack.routers.DefaultRouter']``.


``HAYSTACK_SIGNAL_PROCESSOR``
=============================

**Optional**

This setting controls what ``SignalProcessor`` class is used to handle Django's
signals & keep the search index up-to-date.

An example::

    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

Defaults to ``'haystack.signals.BaseSignalProcessor'``.


``HAYSTACK_DOCUMENT_FIELD``
===========================

**Optional**

This setting controls what fieldname Haystack relies on as the default field
for searching within.

An example::

    HAYSTACK_DOCUMENT_FIELD = 'wall_o_text'

Defaults to ``text``.


``HAYSTACK_SEARCH_RESULTS_PER_PAGE``
====================================

**Optional**

This setting controls how many results are shown per page when using the
included ``SearchView`` and its subclasses.

An example::

    HAYSTACK_SEARCH_RESULTS_PER_PAGE = 50

Defaults to ``20``.


``HAYSTACK_CUSTOM_HIGHLIGHTER``
===============================

**Optional**

This setting allows you to specify your own custom ``Highlighter``
implementation for use with the ``{% highlight %}`` template tag. It should be
the full path to the class.

An example::

    HAYSTACK_CUSTOM_HIGHLIGHTER = 'myapp.utils.BorkHighlighter'

No default is provided. Haystack automatically falls back to the default
implementation.


``HAYSTACK_ITERATOR_LOAD_PER_QUERY``
====================================

**Optional**

This setting controls the number of results that are pulled at once when
iterating through a ``SearchQuerySet``. If you generally consume large portions
at a time, you can bump this up for better performance.

.. note::

    This is not used in the case of a slice on a ``SearchQuerySet``, which
    already overrides the number of results pulled at once.

An example::

    HAYSTACK_ITERATOR_LOAD_PER_QUERY = 100

The default is 10 results at a time.


``HAYSTACK_LIMIT_TO_REGISTERED_MODELS``
=======================================

**Optional**

This setting allows you to control whether or not Haystack will limit the
search results seen to just the models registered. It should be a boolean.

If your search index is never used for anything other than the models
registered with Haystack, you can turn this off and get a small to moderate
performance boost.

An example::

    HAYSTACK_LIMIT_TO_REGISTERED_MODELS = False

Default is ``True``.


``HAYSTACK_ID_FIELD``
=====================

**Optional**

This setting allows you to control what the unique field name used internally
by Haystack is called. Rarely needed unless your field names collide with
Haystack's defaults.

An example::

    HAYSTACK_ID_FIELD = 'my_id'

Default is ``id``.


``HAYSTACK_DJANGO_CT_FIELD``
============================

**Optional**

This setting allows you to control what the content type field name used
internally by Haystack is called. Rarely needed unless your field names
collide with Haystack's defaults.

An example::

    HAYSTACK_DJANGO_CT_FIELD = 'my_django_ct'

Default is ``django_ct``.


``HAYSTACK_DJANGO_ID_FIELD``
============================

**Optional**

This setting allows you to control what the primary key field name used
internally by Haystack is called. Rarely needed unless your field names
collide with Haystack's defaults.

An example::

    HAYSTACK_DJANGO_ID_FIELD = 'my_django_id'

Default is ``django_id``.


``HAYSTACK_IDENTIFIER_METHOD``
==============================

**Optional**

This setting allows you to provide a custom method for
``haystack.utils.get_identifier``. Useful when the default identifier
pattern of <app.label>.<object_name>.<pk> isn't suited to your
needs.

An example::

    HAYSTACK_IDENTIFIER_METHOD = 'my_app.module.get_identifier'

Default is ``haystack.utils.default_get_identifier``.


``HAYSTACK_FUZZY_MIN_SIM``
==========================

**Optional**

This setting allows you to change the required similarity when using ``fuzzy``
filter.

Default is ``0.5``


``HAYSTACK_FUZZY_MAX_EXPANSIONS``
=================================

**Optional**

This setting allows you to change the number of terms fuzzy queries will
expand to when using ``fuzzy`` filter.

Default is ``50``
