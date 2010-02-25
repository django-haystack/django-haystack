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


``HAYSTACK_SITECONF``
=====================

**Required**

This setting controls what module should be loaded to setup your ``SearchSite``.
The module should be on your ``PYTHONPATH`` and should contain only the calls
necessary to setup Haystack to your needs.

The convention is to name this file ``search_sites`` and place it in the same
directory as your ``settings.py`` and/or ``urls.py``.

Valid options are::

    HAYSTACK_SITECONF = 'myproject.search_sites'

No default is provided.


``HAYSTACK_SEARCH_ENGINE``
==========================

**Required**

This setting controls which backend should be used. You should provide the
short name (e.g. ``solr``), not the full filename of the backend (e.g.
``solr_backend.py``).

Valid options are::

    HAYSTACK_SEARCH_ENGINE = 'solr'
    HAYSTACK_SEARCH_ENGINE = 'whoosh'
    HAYSTACK_SEARCH_ENGINE = 'xapian'
    HAYSTACK_SEARCH_ENGINE = 'dummy'

No default is provided.


``HAYSTACK_SEARCH_RESULTS_PER_PAGE``
====================================

**Optional**

This setting controls how many results are shown per page when using the
included ``SearchView`` and its subclasses.

An example::

    HAYSTACK_SEARCH_RESULTS_PER_PAGE = 50

Defaults to ``20``.


``HAYSTACK_INCLUDE_SPELLING``
=============================

**Optional**

This setting controls if spelling suggestions should be included in search
results. This can potentially have performance implications so it is disabled
by default.

An example::

    HAYSTACK_INCLUDE_SPELLING = True

Works for the ``solr`` and ``whoosh`` backends.


``HAYSTACK_SOLR_URL``
=====================

**Required when using the ``solr`` backend**

This setting controls what URL the ``solr`` backend should be connecting to.
This depends on how the user sets up their Solr daemon.

Examples::

    HAYSTACK_SOLR_URL = 'http://localhost:9000/solr/test'
    HAYSTACK_SOLR_URL = 'http://solr.mydomain.com/solr/mysite'

No default is provided.


``HAYSTACK_SOLR_TIMEOUT``
=========================

**Optional when using the ``solr`` backend**

This setting controls the time to wait for a response from Solr in seconds.

Examples::

    HAYSTACK_SOLR_TIMEOUT = 30

The default is 10 seconds.


``HAYSTACK_WHOOSH_PATH``
========================

**Required when using the ``whoosh`` backend**

This setting controls where on the filesystem the Whoosh indexes will be stored.
The user must have the appropriate permissions for reading and writing to this
directory.

Any trailing slashes should be left off.

Finally, you should ensure that this directory is not located within the
document root of your site and that you take appropriate security precautions.

An example::

    HAYSTACK_WHOOSH_PATH = '/home/mysite/whoosh_index'

No default is provided.


``HAYSTACK_WHOOSH_STORAGE``
===========================

**Optional**

This setting controls whether Whoosh uses either the standard file-based
storage or the RAM-based storage.

Note that the RAM-based storage is not permanent and disappears when the
process is ended. This is mostly useful for testing.

Examples::

    HAYSTACK_WHOOSH_STORAGE = 'file'
    HAYSTACK_WHOOSH_STORAGE = 'ram'

The default is 'file'.


``HAYSTACK_WHOOSH_POST_LIMIT``
==============================

**Optional**

This setting controls how large of a document Whoosh will accept when writing.

Examples::

    HAYSTACK_WHOOSH_POST_LIMIT = 256 * 1024 * 1024

The default is 128 * 1024 * 1024.


``HAYSTACK_XAPIAN_PATH``
========================

**Required when using the ``xapian`` backend**

This setting controls where on the filesystem the Xapian indexes will be stored.
The user must have the appropriate permissions for reading and writing to this
directory.

Any trailing slashes should be left off.

Finally, you should ensure that this directory is not located within the
document root of your site and that you take appropriate security precautions.

An example::

    HAYSTACK_XAPIAN_PATH = '/home/mysite/xapian_index'

No default is provided.


``HAYSTACK_BATCH_SIZE``
=======================

**Optional**

This setting controls the number of model instances loaded at a time while
reindexing. This affects how often the search indexes must merge (an intensive
operation).

An example::

    HAYSTACK_BATCH_SIZE = 100

The default is 1000 models per commit.


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


``HAYSTACK_ENABLE_REGISTRATIONS``
=================================

**Optional**

This setting allows you to control whether or not Haystack will manage it's own
registrations at start-up. It should be a boolean.

An example::

    HAYSTACK_ENABLE_REGISTRATIONS = False

Default is ``True``.

.. warning::

    Setting this to ``False`` prevents Haystack from doing any imports, which
    means that no ``SearchIndex`` classes will get registered, no signals will
    get hooked up and any use of ``SearchQuerySet`` without further work will
    yield no results. You can manually import your ``SearchIndex`` classes in
    other files (like your views or elsewhere). In short, Haystack will still
    be available but essentially in an un-initialized state.
    
    You should ONLY use this setting if you're using another third-party
    application that causes tracebacks/import errors when used in conjunction
    with Haystack.
