Welcome to Haystack!
====================

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Elasticsearch_, Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Elasticsearch: http://elasticsearch.org/
.. _Whoosh: https://bitbucket.org/mchaput/whoosh/
.. _Xapian: http://xapian.org/


.. note::

    This documentation represents the current version of Haystack. For old versions of the documentation:

    * v2.4.X: https://django-haystack.readthedocs.io/en/v2.4.1/
    * v2.3.X: https://django-haystack.readthedocs.io/en/v2.3.0/
    * v2.2.X: https://django-haystack.readthedocs.io/en/v2.2.0/
    * v2.1.X: https://django-haystack.readthedocs.io/en/v2.1.0/
    * v2.0.X: https://django-haystack.readthedocs.io/en/v2.0.0/
    * v1.2.X: https://django-haystack.readthedocs.io/en/v1.2.7/
    * v1.1.X: https://django-haystack.readthedocs.io/en/v1.1/

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

   changelog
   contributing
   python3
   migration_from_1_to_2


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
   signal_processors
   multiple_index
   rich_content_extraction
   spatial
   admin


Reference
---------

If you're an experienced user and are looking for a reference, you may be
looking for API documentation and advanced usage as detailed in:

.. toctree::
   :maxdepth: 2

   searchqueryset_api
   searchindex_api
   inputtypes
   searchfield_api
   searchresult_api
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

* Python 2.7+ or Python 3.3+
* A supported version of Django: https://www.djangoproject.com/download/#supported-versions

Additionally, each backend has its own requirements. You should refer to
:doc:`installing_search_engines` for more details.
