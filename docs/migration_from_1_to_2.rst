.. _ref-migration_from_1_to_2:

===========================================
Migrating From Haystack 1.X to Haystack 2.X
===========================================

Haystack introduced several backward-incompatible changes in the process of
moving from the 1.X series to the 2.X series. These were done to clean up the
API, to support new features & to clean up problems in 1.X. At a high level,
they consisted of:

* The removal of ``SearchSite`` & ``haystack.site``.
* The removal of ``handle_registrations`` & ``autodiscover``.
* The addition of multiple index support.
* The addition of ``SignalProcessors`` & the removal of ``RealTimeSearchIndex``.
* The removal/renaming of various settings.

This guide will help you make the changes needed to be compatible with Haystack
2.X.


Settings
========

Most prominently, the old way of specifying a backend & its settings has changed
to support the multiple index feature. A complete Haystack 1.X example might
look like::

    HAYSTACK_SEARCH_ENGINE = 'solr'
    HAYSTACK_SOLR_URL = 'http://localhost:9001/solr/default'
    HAYSTACK_SOLR_TIMEOUT = 60 * 5
    HAYSTACK_INCLUDE_SPELLING = True
    HAYSTACK_BATCH_SIZE = 100

    # Or...
    HAYSTACK_SEARCH_ENGINE = 'whoosh'
    HAYSTACK_WHOOSH_PATH = '/home/search/whoosh_index'
    HAYSTACK_WHOOSH_STORAGE = 'file'
    HAYSTACK_WHOOSH_POST_LIMIT = 128 * 1024 * 1024
    HAYSTACK_INCLUDE_SPELLING = True
    HAYSTACK_BATCH_SIZE = 100

    # Or...
    HAYSTACK_SEARCH_ENGINE = 'xapian'
    HAYSTACK_XAPIAN_PATH = '/home/search/xapian_index'
    HAYSTACK_INCLUDE_SPELLING = True
    HAYSTACK_BATCH_SIZE = 100

In Haystack 2.X, you can now supply as many backends as you like, so all of the
above settings can now be active at the same time. A translated set of settings
would look like::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:9001/solr/default',
            'TIMEOUT': 60 * 5,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
        },
        'autocomplete': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': '/home/search/whoosh_index',
            'STORAGE': 'file',
            'POST_LIMIT': 128 * 1024 * 1024,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
        },
        'slave': {
            'ENGINE': 'xapian_backend.XapianEngine',
            'PATH': '/home/search/xapian_index',
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
        },
    }

You are required to have at least one connection listed within
``HAYSTACK_CONNECTIONS``, it must be named ``default`` & it must have a valid
``ENGINE`` within it. Bare minimum looks like::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine'
        }
    }

The key for each backend is an identifier you use to describe the backend within
your app. You should refer to the :ref:`ref-multiple_index` documentation for
more information on using the new multiple indexes & routing features.

Also note that the ``ENGINE`` setting has changed from a lowercase "short name"
of the engine to a full path to a new ``Engine`` class within the backend.
Available options are:

* ``haystack.backends.solr_backend.SolrEngine``
* ``haystack.backends.whoosh_backend.WhooshEngine``
* ``haystack.backends.simple_backend.SimpleEngine``

Additionally, the following settings were outright removed & will generate
an exception if found:

* ``HAYSTACK_SITECONF`` - Remove this setting & the file it pointed to.
* ``HAYSTACK_ENABLE_REGISTRATIONS``
* ``HAYSTACK_INCLUDE_SPELLING``


Backends
========

The ``dummy`` backend was outright removed from Haystack, as it served very
little use after the ``simple`` (pure-ORM-powered) backend was introduced.

If you wrote a custom backend, please refer to the "Custom Backends" section
below.


Indexes
=======

The other major changes affect the ``SearchIndex`` class. As the concept of
``haystack.site`` & ``SearchSite`` are gone, you'll need to modify your indexes.

A Haystack 1.X index might've looked like::

    import datetime
    from haystack.indexes import *
    from haystack import site
    from myapp.models import Note


    class NoteIndex(SearchIndex):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')

        def get_queryset(self):
            """Used when the entire index for model is updated."""
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())


    site.register(Note, NoteIndex)

A converted Haystack 2.X index should look like::

    import datetime
    from haystack import indexes
    from myapp.models import Note


    class NoteIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def index_queryset(self, using=None):
            """Used when the entire index for model is updated."""
            return self.get_model().objects.filter(pub_date__lte=datetime.datetime.now())

Note the import on ``site`` & the registration statements are gone. Newly added
are is the ``NoteIndex.get_model`` method. This is a **required** method &
should simply return the ``Model`` class the index is for.

There's also a new, additional class added to the ``class`` definition. The
``indexes.Indexable`` class is a simple mixin that serves to identify the
classes Haystack should automatically discover & use. If you have a custom
base class (say ``QueuedSearchIndex``) that other indexes inherit from, simply
leave the ``indexes.Indexable`` off that declaration & Haystack won't try to
use it.

Additionally, the name of the ``document=True`` field is now enforced to be
``text`` across all indexes. If you need it named something else, you should
set the ``HAYSTACK_DOCUMENT_FIELD`` setting. For example::

    HAYSTACK_DOCUMENT_FIELD = 'pink_polka_dot'

Finally, the ``index_queryset`` method should supplant the ``get_queryset``
method. This was present in the Haystack 1.2.X series (with a deprecation warning
in 1.2.4+) but has been removed in Haystack v2.

Finally, if you were unregistering other indexes before, you should make use of
the new ``EXCLUDED_INDEXES`` setting available in each backend's settings. It
should be a list of strings that contain the Python import path to the indexes
that should not be loaded & used. For example::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:9001/solr/default',
            'EXCLUDED_INDEXES': [
                # Imagine that these indexes exist. They don't.
                'django.contrib.auth.search_indexes.UserIndex',
                'third_party_blog_app.search_indexes.EntryIndex',
            ]
        }
    }

This allows for reliable swapping of the index that handles a model without
relying on correct import order.


Removal of ``RealTimeSearchIndex``
==================================

Use of the ``haystack.indexes.RealTimeSearchIndex`` is no longer valid. It has
been removed in favor of ``RealtimeSignalProcessor``. To migrate, first change
the inheritance of all your ``RealTimeSearchIndex`` subclasses to use
``SearchIndex`` instead::

    # Old.
    class MySearchIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
        # ...


    # New.
    class MySearchIndex(indexes.SearchIndex, indexes.Indexable):
        # ...

Then update your settings to enable use of the ``RealtimeSignalProcessor``::

    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'


Done!
=====

For most basic uses of Haystack, this is all that is necessary to work with
Haystack 2.X. You should rebuild your index if needed & test your new setup.


Advanced Uses
=============

Swapping Backend
----------------

If you were manually swapping the ``SearchQuery`` or ``SearchBackend`` being
used by ``SearchQuerySet`` in the past, it's now preferable to simply setup
another connection & use the ``SearchQuerySet.using`` method to select that
connection instead.

Also, if you were manually instantiating ``SearchBackend`` or ``SearchQuery``,
it's now preferable to rely on the connection's engine to return the right
thing. For example::

    from haystack import connections
    backend = connections['default'].get_backend()
    query = connections['default'].get_query()


Custom Backends
---------------

If you had written a custom ``SearchBackend`` and/or custom ``SearchQuery``,
there's a little more work needed to be Haystack 2.X compatible.

You should, but don't have to, rename your ``SearchBackend`` & ``SearchQuery``
classes to be more descriptive/less collide-y. For example,
``solr_backend.SearchBackend`` became ``solr_backend.SolrSearchBackend``. This
prevents non-namespaced imports from stomping on each other.

You need to add a new class to your backend, subclassing ``BaseEngine``. This
allows specifying what ``backend`` & ``query`` should be used on a connection
with less duplication/naming trickery. It goes at the bottom of the file (so
that the classes are defined above it) and should look like::

    from haystack.backends import BaseEngine
    from haystack.backends.solr_backend import SolrSearchQuery

    # Code then...

    class MyCustomSolrEngine(BaseEngine):
        # Use our custom backend.
        backend = MySolrBackend
        # Use the built-in Solr query.
        query = SolrSearchQuery

Your ``HAYSTACK_CONNECTIONS['default']['ENGINE']`` should then point to the
full Python import path to your new ``BaseEngine`` subclass.

Finally, you will likely have to adjust the ``SearchBackend.__init__`` &
``SearchQuery.__init__``, as they have changed significantly. Please refer to
the commits for those backends.
