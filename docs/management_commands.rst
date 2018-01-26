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
following arguments:

    ``--noinput``:
        If provided, the interactive prompts are skipped and the index is
        unceremoniously wiped out.
    ``--verbosity``:
        Accepted but ignored.
    ``--using``:
        Update only the named backend (can be used multiple times). By default,
        all backends will be updated.
    ``--nocommit``:
        If provided, it will pass commit=False to the backend.  This means that the
        update will not become immediately visible and will depend on another explicit commit
        or the backend's commit strategy to complete the update.

By default, this is an **INTERACTIVE** command and assumes that you do **NOT**
wish to delete the entire index.

.. note::

    The ``--nocommit`` argument is only supported by the Solr backend.

.. warning::

  Depending on the backend you're using, this may simply delete the entire
  directory, so be sure your ``HAYSTACK_CONNECTIONS[<alias>]['PATH']`` setting is correctly
  pointed at just the index directory.


``update_index``
================

.. note::

    If you use the ``--start/--end`` flags on this command, you'll need to
    install dateutil_ to handle the datetime parsing.

    .. _dateutil: http://pypi.python.org/pypi/python-dateutil/1.5

The ``update_index`` command will freshen all of the content in your index. It
iterates through all indexed models and updates the records in the index. In
addition to the standard management command options, it accepts the following
arguments:

    ``--age``:
        Number of hours back to consider objects new. Useful for nightly
        reindexes (``--age=24``). Requires ``SearchIndexes`` to implement
        the ``get_updated_field`` method. Default is ``None``.
    ``--start``:
        The start date for indexing within. Can be any dateutil-parsable string,
        recommended to be YYYY-MM-DDTHH:MM:SS. Requires ``SearchIndexes`` to
        implement the ``get_updated_field`` method. Default is ``None``.
    ``--end``:
        The end date for indexing within. Can be any dateutil-parsable string,
        recommended to be YYYY-MM-DDTHH:MM:SS. Requires ``SearchIndexes`` to
        implement the ``get_updated_field`` method. Default is ``None``.
    ``--batch-size``:
        Number of items to index at once. Default is 1000.
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
        Update only the named backend (can be used multiple times). By default,
        all backends will be updated.
    ``--nocommit``:
        If provided, it will pass commit=False to the backend.  This means that the
        updates will not become immediately visible and will depend on another explicit commit
        or the backend's commit strategy to complete the update.

.. note::

    The ``--nocommit`` argument is only supported by the Solr and ElasticSearch backends.

Examples::

    # Update everything.
    ./manage.py update_index --settings=settings.prod

    # Update everything with lots of information about what's going on.
    ./manage.py update_index --settings=settings.prod --verbosity=2

    # Update everything, cleaning up after deleted models.
    ./manage.py update_index --remove --settings=settings.prod

    # Update everything changed in the last 2 hours.
    ./manage.py update_index --age=2 --settings=settings.prod

    # Update everything between Dec. 1, 2011 & Dec 31, 2011
    ./manage.py update_index --start='2011-12-01T00:00:00' --end='2011-12-31T23:59:59' --settings=settings.prod

    # Update just a couple apps.
    ./manage.py update_index blog auth comments --settings=settings.prod

    # Update just a single model (in a complex app).
    ./manage.py update_index auth.User --settings=settings.prod

    # Crazy Go-Nuts University
    ./manage.py update_index events.Event media news.Story --start='2011-01-01T00:00:00 --remove --using=hotbackup --workers=12 --verbosity=2 --settings=settings.prod

.. note::

    This command *ONLY* updates records in the index. It does *NOT* handle
    deletions unless the ``--remove`` flag is provided. You might consider
    a queue consumer if the memory requirements for ``--remove`` don't
    fit your needs. Alternatively, you can use the
    ``RealtimeSignalProcessor``, which will automatically handle deletions.


``rebuild_index``
=================

A shortcut for ``clear_index`` followed by ``update_index``. It accepts any/all
of the arguments of the following arguments:

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
        unceremoniously wiped out.
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
        Update only the named backend (can be used multiple times). By default,
        all backends will be updated.
    ``--nocommit``:
        If provided, it will pass commit=False to the backend.  This means that the
        update will not become immediately visible and will depend on another explicit commit
        or the backend's commit strategy to complete the update.

For when you really, really want a completely rebuilt index.


``build_solr_schema``
=====================

Once all of your ``SearchIndex`` classes are in place, this command can be used
to generate the XML schema Solr needs to handle the search data.  Generates a
Solr schema and solrconfig file that reflects the indexes using templates under
a Django template dir 'search_configuration/\*.xml'. If none are found, then
provides defaults suitable for Solr 6.4.

It accepts the following arguments:

    ``--filename``:
        If provided, renders schema.xml from the template directory directly to
        a file instead of stdout. Does not render solrconfig.xml
    ``--using``:
        Update only the named backend (can be used multiple times). By default
        all backends will be updated.
    ``--configure-directory``:
        If provided, attempts to configure a core located in the given directory
        by removing the ``managed-schema.xml`` (renaming if it exists), configuring
        the core by rendering the ``schema.xml`` and ``solrconfig.xml`` templates
        provided in the Django project's ``TEMPLATE_DIR/search_configuration``
        directories.
    ``--reload-core``:
        If provided, attempts to automatically reload the solr core via the urls
        in the ``URL`` and ``ADMIN_URL`` settings of the Solr entry in
        ``HAYSTACK_CONNECTIONS``. Both *must* be provided.

.. note::
   ``build_solr_schema --configure-directory=<dir>`` can be used in isolation to
   drop configured files anywhere one might want for staging to one or more solr
   instances through arbitrary means.  It will render all template files in the
   directory into the ``configure-directory``

   ``build_solr_schema --configure-directory=<dir> --reload-core`` can be used
   together to reconfigure and reload a core located on a filesystem accessible
   to Django in a one-shot mechanism with no further requirements (assuming
   there are no errors in the template or configuration)

.. note::
    ``build_solr_schema`` uses templates to generate the output files. Haystack
    provides default templates for ``schema.xml`` and ``solrconfig.xml`` that
    are solr 6.5 compatible using some sensible defaults. If you would like to
    provide your own template, you will need to place it in
    ``search_configuration/`` inside a directory specified by your app's
    template directories settings. Examples::

        /myproj/myapp/templates/search_configuration/schema.xml
        /myproj/myapp/templates/search_configuration/sorlconfig.xml
        /myproj/myapp/templates/search_configuration/otherfile.xml
        # ...or...
        /myproj/templates/search_configuration/schema.xml
        /myproj/templates/search_configuration/sorlconfig.xml
        /myproj/myapp/templates/search_configuration/otherfile.xml

.. warning::
    This command does NOT automatically update the ``schema.xml`` file for you
    all by itself.  You must use --filename or --configure-directory to achieve
    this.


``haystack_info``
=================

Provides some basic information about how Haystack is setup and what models it
is handling. It accepts no arguments. Useful when debugging or when using
Haystack-enabled third-party apps.
