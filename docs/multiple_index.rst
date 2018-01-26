.. _ref-multiple_index:

================
Multiple Indexes
================

Much like Django's `multiple database support`_, Haystack has "multiple index"
support. This allows you to talk to several different engines at the same time.
It enables things like master-slave setups, multiple language indexing,
separate indexes for general search & autocomplete as well as other options.

.. _`multiple database support`: http://docs.djangoproject.com/en/1.3/topics/db/multi-db/


Specifying Available Connections
================================

You can supply as many backends as you like, each with a descriptive name. A
complete setup that accesses all backends might look like::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:9001/solr/default',
            'TIMEOUT': 60 * 5,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'SILENTLY_FAIL': True,
        },
        'autocomplete': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': '/home/search/whoosh_index',
            'STORAGE': 'file',
            'POST_LIMIT': 128 * 1024 * 1024,
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'SILENTLY_FAIL': True,
        },
        'slave': {
            'ENGINE': 'xapian_backend.XapianEngine',
            'PATH': '/home/search/xapian_index',
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
            'SILENTLY_FAIL': True,
        },
        'db': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
            'SILENTLY_FAIL': True,
        }
    }

You are required to have at least one connection listed within
``HAYSTACK_CONNECTIONS``, it must be named ``default`` & it must have a valid
``ENGINE`` within it.


Management Commands
===================

All management commands that manipulate data use **ONLY** one connection at a
time. By default, they use the ``default`` index but accept a ``--using`` flag
to specify a different connection. For example::

    ./manage.py rebuild_index --noinput --using=whoosh


Automatic Routing
=================

To make the selection of the correct index easier, Haystack (like Django) has
the concept of "routers". All provided routers are checked whenever a read or
write happens, in the order in which they are defined.

For read operations (when a search query is executed), the ``for_read`` method
of each router is called, until one of them returns an index, which is used for
the read operation.

For write operations (when a delete or update is executed), the ``for_write``
method of each router is called, and the results are aggregated. All of the
indexes that were returned are then updated.

Haystack ships with a ``DefaultRouter`` enabled. It looks like::

    class DefaultRouter(BaseRouter):
        def for_read(self, **hints):
            return DEFAULT_ALIAS
        
        def for_write(self, **hints):
            return DEFAULT_ALIAS

This means that the default index is used for all read and write operations.

If the ``for_read`` or ``for_write`` method doesn't exist or returns ``None``,
that indicates that the current router can't handle the data. The next router
is then checked.

The ``for_write`` method can return either a single string representing an
index name, or an iterable of such index names. For example::

    class UpdateEverythingRouter(BaseRouter):
        def for_write(self, **hints):
            return ('myindex1', 'myindex2')

The ``hints`` passed can be anything that helps the router make a decision. This
data should always be considered optional & be guarded against. At current,
``for_write`` receives an ``index`` option (pointing to the ``SearchIndex``
calling it) while ``for_read`` may receive ``models`` (being a list of ``Model``
classes the ``SearchQuerySet`` may be looking at).

You may provide as many routers as you like by overriding the
``HAYSTACK_ROUTERS`` setting. For example::

    HAYSTACK_ROUTERS = ['myapp.routers.MasterRouter', 'myapp.routers.SlaveRouter', 'haystack.routers.DefaultRouter']

Master-Slave Example
--------------------

The ``MasterRouter`` & ``SlaveRouter`` might look like::

    from haystack import routers
    
    
    class MasterRouter(routers.BaseRouter):
        def for_write(self, **hints):
            return 'master'
        
        def for_read(self, **hints):
            return None
    
    
    class SlaveRouter(routers.BaseRouter):
        def for_write(self, **hints):
            return None
        
        def for_read(self, **hints):
            return 'slave'

The observant might notice that since the methods don't overlap, this could be
combined into one ``Router`` like so::

    from haystack import routers
    
    
    class MasterSlaveRouter(routers.BaseRouter):
        def for_write(self, **hints):
            return 'master'
        
        def for_read(self, **hints):
            return 'slave'


Manually Selecting
==================

There may be times when automatic selection of the correct index is undesirable,
such as when fixing erroneous data in an index or when you know exactly where
data should be located.

For this, the ``SearchQuerySet`` class allows for manually selecting the index
via the ``SearchQuerySet.using`` method::

    from haystack.query import SearchQuerySet
    
    # Uses the routers' opinion.
    sqs = SearchQuerySet().auto_query('banana')
    
    # Forces the default.
    sqs = SearchQuerySet().using('default').auto_query('banana')
    
    # Forces the slave connection (presuming it was setup).
    sqs = SearchQuerySet().using('slave').auto_query('banana')

.. warning::

  Note that the models a ``SearchQuerySet`` is trying to pull from must all come
  from the same index. Haystack is not able to combine search queries against
  different indexes.


Custom Index Selection
======================

If a specific backend has been selected, the ``SearchIndex.index_queryset`` and
``SearchIndex.read_queryset`` will receive the backend name, giving indexes the
opportunity to customize the returned queryset.

For example, a site which uses separate indexes for recent items and older
content might define ``index_queryset`` to filter the items based on date::

        def index_queryset(self, using=None):
            qs = Note.objects.all()
            archive_limit = datetime.datetime.now() - datetime.timedelta(days=90)

            if using == "archive":
                return qs.filter(pub_date__lte=archive_limit)
            else:
                return qs.filter(pub_date__gte=archive_limit)


Multi-lingual Content
---------------------

Most search engines require you to set the language at the index level. For
example, a multi-lingual site using Solr can use `multiple cores <http://wiki.apache.org/solr/CoreAdmin>`_ and corresponding Haystack
backends using the language name. Under this scenario, queries are simple::

    sqs = SearchQuerySet.using(lang).auto_query(…)

During index updates, the Index's ``index_queryset`` method will need to filter
the items to avoid sending the wrong content to the search engine::

        def index_queryset(self, using=None):
            return Post.objects.filter(language=using)
