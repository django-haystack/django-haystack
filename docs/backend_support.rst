===============
Backend Support
===============


Supported Backends
==================

* Solr_
* Lucene_
* Xapian_
* `Hyper Estraier`_
* Sphinx_

.. _Solr: http://lucene.apache.org/solr/
.. _Lucene: http://lucene.apache.org/java/
.. _Xapian: http://xapian.org/
.. _Hyper Estraier: http://hyperestraier.sourceforge.net/
.. _Sphinx: http://www.sphinxsearch.com/


Backend Capabilities
====================

Solr
----

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: pysolr

Lucene
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: pyluncene

Xapian
------

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: xappy?

Hyper Estraier
--------------

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Highlighting
* Requires: SWIG bindings

Sphinx
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: sphinxapi.py (Comes with Sphinx)


+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields | Highlighting |
+================+========================+=====================+================+============+==========+===============+==============+
| Solr           | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Lucene         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Xapian         | Yes                    | Yes                 | Yes            | No         | Yes      | Yes           | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Hyper Estraier | Yes                    | Yes                 | Yes            | No         | No       | No            | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Sphinx         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
