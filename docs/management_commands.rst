.. _ref-management-commands:

===================
Management Commands
===================

Haystack comes with several management commands to make working with Haystack
easier.


``clear_index``
===============

The ``clear_index`` command wipes out your entire search index. It accepts no
arguments. Use with caution.

This is an **INTERACTIVE** command and assumes that you do **NOT** wish to
delete the entire index.


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

Using ``--verbosity=2`` with this command shows individual batches being sent,
which is useful when debugging.

.. note::

    This command *ONLY* updates records in the index. It does *NOT* handle
    deletions, so you may need to write a separate script that handles deleted
    models, such as a queue consumer or something that runs through all records
    and tries to load the model for it. Alternatively, you can use the
    ``RealTimeSearchIndex``, which will automatically handle deletions.
    

``rebuild_index``
=================

A shortcut for ``clear_index`` followed by ``update_index``. It accepts no
arguments. For when you really, really want a completely rebuilt index.


``build_solr_schema``
=====================

Once all of your ``SearchIndex`` classes are in place, this command can be used
to generate the XML schema Solr needs to handle the search data. It accepts no
arguments.

.. warning:

    This command does NOT update the ``schema.xml`` file for you. You have to
    copy-paste (or redirect) the output to the correct file. Haystack has no
    way of knowing where your Solr is setup (or if it's even on the same
    machine), hence the manual step.


``haystack_info``
=================

Provides some basic information about how Haystack is setup and what models it
is handling. It accepts no arguments. Useful when debugging or when using
Haystack-enabled third-party apps.
