.. ref-debugging:

==================
Debugging Haystack
==================

There are some common problems people run into when using Haystack for the first
time. Some of the common problems and things to try appear below.

.. note::

    As a general suggestion, your best friend when debugging an issue is to
    use the ``pdb`` library included with Python. By dropping a
    ``import pdb; pdb.set_trace()`` in your code before the issue occurs, you
    can step through and examine variable/logic as you progress through. Make
    sure you don't commit those ``pdb`` lines though.


"No module named haystack."
===========================

This problem usually occurs when first adding Haystack to your project.

* Are you using the ``haystack`` directory within your ``django-haystack``
  checkout/install?
* Is the ``haystack`` directory on your ``PYTHONPATH``? Alternatively, is
  ``haystack`` symlinked into your project?
* Start a Django shell (``./manage.py shell``) and try ``import haystack``.
  You may receive a different, more descriptive error message.
* Double-check to ensure you have no circular imports. (i.e. module A tries
  importing from module B which is trying to import from module A.)


"No results found." (On the web page)
=====================================

Several issues can cause no results to be found. Most commonly it is either
not running a ``rebuild_index`` to populate your index or having a blank
``document=True`` field, resulting in no content for the engine to search on.

* Do you have a ``search_sites.py`` that runs ``haystack.autodiscover``?
* Have you registered your models with the main ``haystack.site`` (usually
  within your ``search_indexes.py``)?
* Do you have data in your database?
* Have you run a ``./manage.py rebuild_index`` to index all of your content?
* Start a Django shell (``./manage.py shell``) and try::

  >>> from haystack.query import SearchQuerySet
  >>> sqs = SearchQuerySet().all()
  >>> sqs.count()

* You should get back an integer > 0. If not, check the above and reindex.

  >>> sqs[0] # Should get back a SearchResult object.
  >>> sqs[0].id # Should get something back like 'myapp.mymodel.1'.
  >>> sqs[0].text # ... or whatever your document=True field is.

* If you get back either ``u''`` or ``None``, it means that your data isn't
  making it into the main field that gets searched. You need to check that the
  field either has a template that uses the model data, a ``model_attr`` that
  pulls data directly from the model or a ``prepare/prepare_FOO`` method that
  populates the data at index time.
* Check the template for your search page and ensure it is looping over the
  results properly. Also ensure that it's either accessing valid fields coming
  back from the search engine or that it's trying to access the associated
  model via the ``{{ result.object.foo }}`` lookup.


"LockError: [Errno 17] File exists: '/path/to/whoosh_index/_MAIN_LOCK'"
=======================================================================

This is a Whoosh-specific traceback. It occurs when the Whoosh engine in one
process/thread is locks the index files for writing while another process/thread
tries to access them. This is a common error when using ``RealTimeSearchIndex``
with Whoosh under any kind of load, which is why it's only recommended for
small sites or development.

A way to solve this is to subclass ``SearchIndex`` instead::

    from haystack import indexes
    
    # Change from:
    # 
    #   class MySearchIndex(indexes.RealTimeSearchIndex):
    # 
    # to:
    class MySearchIndex(indexes.SearchIndex):
        ...

The final step is to set up a cron job that runs
``./manage.py rebuild_index`` (optionally with ``--age=24``) that runs nightly
(or however often you need) to refresh the search indexes.

The downside to this is that you lose real-time search. For many people, this
isn't an issue and this will allow you to scale Whoosh up to a much higher
traffic. If this is not acceptable, you should investigate either the Solr or
Xapian backends.
