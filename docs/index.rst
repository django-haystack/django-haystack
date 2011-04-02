Welcome to Haystack!
====================

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Whoosh: http://whoosh.ca/
.. _Xapian: http://xapian.org/


.. note::

    This documentation represents the development version of Haystack. For
    old versions of the documentation: `1.0`_, `1.1`_.

.. _`1.0`: http://docs.haystacksearch.org/1.0/
.. _`1.1`: http://docs.haystacksearch.org/1.1/

Getting Started
---------------

If you're new to Haystack, you may want to start with these documents to get
you up and running:

.. toctree::
   :maxdepth: 2
   
   tutorial
   
.. toctree::
   :maxdepth: 1
   
   views_and_forms
   templatetags
   glossary
   management_commands
   faq
   who_uses
   other_apps
   installing_search_engines
   debugging


Advanced Uses
-------------

Once you've got Haystack working, here are some of the more complex features
you may want to include in your application.

.. toctree::
   :maxdepth: 1
   
   best_practices
   highlighting
   faceting
   autocomplete
   boost
   do_not_try_this_at_home


Reference
---------

If you're an experienced user and are looking for a reference, you may be
looking for API documentation and advanced usage as detailed in:

.. toctree::
   :maxdepth: 2
   
   searchqueryset_api
   searchindex_api
   searchfield_api
   searchresult_api
   searchsite_api
   searchquery_api
   searchbackend_api
   
   architecture_overview
   backend_support
   settings
   utils


Developing
----------

Finally, if you're looking to help out with the development of Haystack,
the following links should help guide you on running tests and creating
additional backends:

.. toctree::
   :maxdepth: 1
   
   running_tests
   creating_new_backends


Requirements
------------

Haystack has a relatively easily-met set of requirements.

* Python 2.4+ (may work on 2.3 but untested)
* Django 1.0+

Additionally, each backend has its own requirements. You should refer to
:doc:`installing_search_engines` for more details.
