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
