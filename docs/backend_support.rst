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
* Requires: pysolr

Lucene
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Requires: pyluncene (owwie?)

Xapian
------

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Faceting
* Stored (non-indexed) fields
* Requires: xappy?

Hyper Estraier
--------------

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Requires: SWIG bindings

Sphinx
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Requires: sphinxapi.py (Comes with Sphinx)


+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields |
+================+========================+=====================+================+============+==========+===============+
| Solr           | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
| Lucene         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
| Xapian         | Yes                    | Yes                 | Yes            | No         | Yes      | Yes           |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
| Hyper Estraier | Yes                    | Yes                 | Yes            | No         | No       | No            |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
| Sphinx         | Yes                    | Yes                 | No             | Yes        | No       | Yes           |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+
