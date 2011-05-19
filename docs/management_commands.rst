.. _ref-management-commands:

===================
Management Commands
===================

Haystack comes with several management commands to make working with Haystack
easier.


``clear_index``
===============

The ``clear_index`` command wipes out your entire search index. Use with
caution. In addition to the standard management command options, it accepts the
following arguments::

    ``--noinput``:
        If provided, the interactive prompts are skipped and the index is
        uncerimoniously wiped out.
    ``--verbosity``:
        Accepted but ignored.
    ``--using``:
        If provided, determines which connection should be used. Default is
        ``default``.

By default, this is an **INTERACTIVE** command and assumes that you do **NOT**
wish to delete the entire index.

.. warning::

  Depending on the backend you're using, this may simply delete the entire
  directory, so be sure your ``HAYSTACK_CONNECTIONS[<alias>]['PATH']`` setting is correctly
  pointed at just the index directory.


``update_index``
================

The ``update_index`` command will freshen all of the content in your index. It
iterates through all indexed models and updates the records in the index. In
addition to the standard management command options, it accepts the following
arguments::

    ``--age``:
        Number of hours back to consider objects new. Useful for nightly
        reindexes (``--age=24``). Requires ``SearchIndexes`` to implement
        the ``get_updated_field`` method.
    ``--batch-size``:
        Number of items to index at once. Default is 1000.
    ``--site``:
        The site object to use when reindexing (like `search_sites.mysite`).
    ``--remove``:
        Remove objects from the index that are no longer present in the
        database.
    ``--workers``:
        Allows for the use multiple workers to parallelize indexing. Requires
        ``multiprocessing``.
    ``--verbosity``:
        If provided, dumps out more information about what's being done.
        
          * ``0`` = No output
          * ``1`` = Minimal output describing what models were indexed
            and how many records.
          * ``2`` = Full output, including everything from ``1`` plus output
            on each batch that is indexed, which is useful when debugging.
    ``--using``:
        If provided, determines which connection should be used. Default is
        ``default``.

.. note::

    This command *ONLY* updates records in the index. It does *NOT* handle
    deletions unless the ``--remove`` flag is provided. You might consider
    a queue consumer if the memory requirements for ``--remove`` don't
    fit your needs. Alternatively, you can use the
    ``RealTimeSearchIndex``, which will automatically handle deletions.
    

``rebuild_index``
=================

A shortcut for ``clear_index`` followed by ``update_index``. It accepts any/all
of the arguments of the following arguments::

    ``--age``:
        Number of hours back to consider objects new. Useful for nightly
        reindexes (``--age=24``). Requires ``SearchIndexes`` to implement
        the ``get_updated_field`` method.
    ``--batch-size``:
        Number of items to index at once. Default is 1000.
    ``--site``:
        The site object to use when reindexing (like `search_sites.mysite`).
    ``--noinput``:
        If provided, the interactive prompts are skipped and the index is
        uncerimoniously wiped out.
    ``--remove``:
        Remove objects from the index that are no longer present in the
        database.
    ``--verbosity``:
        If provided, dumps out more information about what's being done.
        
          * ``0`` = No output
          * ``1`` = Minimal output describing what models were indexed
            and how many records.
          * ``2`` = Full output, including everything from ``1`` plus output
            on each batch that is indexed, which is useful when debugging.
    ``--using``:
        If provided, determines which connection should be used. Default is
        ``default``.

For when you really, really want a completely rebuilt index.


``build_solr_schema``
=====================

Once all of your ``SearchIndex`` classes are in place, this command can be used
to generate the XML schema Solr needs to handle the search data. It accepts the
following arguments::

    ``--filename``:
        If provided, directs output to a file instead of stdout.
    ``--using``:
        If provided, determines which connection should be used. Default is
        ``default``.

.. warning:

    This command does NOT update the ``schema.xml`` file for you. You either
    have to specify a ``filename`` flag or have to
    copy-paste (or redirect) the output to the correct file. Haystack has no
    way of knowing where your Solr is setup (or if it's even on the same
    machine), hence the manual step.


``haystack_info``
=================

Provides some basic information about how Haystack is setup and what models it
is handling. It accepts no arguments. Useful when debugging or when using
Haystack-enabled third-party apps.
