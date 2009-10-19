.. _ref-backend-support:

===============
Backend Support
===============


Supported Backends
==================

* Solr_
* Lucene_
* Whoosh_

.. _Solr: http://lucene.apache.org/solr/
.. _Lucene: http://lucene.apache.org/java/
.. _Whoosh: http://whoosh.ca/


Backend Capabilities
====================

Solr
----

**Complete & included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: pysolr (`GitHub version`_) + Solr 1.3+

.. _Github version: http://github.com/toastdriven/pysolr

Lucene
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: pylucene

Whoosh
------

**Complete & included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: whoosh (`GitHub fork`_)

.. _Github fork: http://github.com/toastdriven/whoosh


+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields | Highlighting |
+================+========================+=====================+================+============+==========+===============+==============+
| Solr           | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Lucene         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Whoosh         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+


Wishlist
========

The following are search backends that would be nice to have in Haystack but are
licensed in a way that prevents them from being officially bundled. If the
community expresses interest in any of these, there may be future development.

* Xapian_
* Sphinx_
* `Hyper Estraier`_

.. _Xapian: http://xapian.org/
.. _Sphinx: http://www.sphinxsearch.com/
.. _Hyper Estraier: http://hyperestraier.sourceforge.net/

Xapian
------

**Complete but not included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* "More Like This" functionality
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: xapian bindings included with Xapian

Sphinx
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: sphinxapi.py (Comes with Sphinx)

Hyper Estraier
--------------

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Highlighting
* Requires: SWIG bindings

+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields | Highlighting |
+================+========================+=====================+================+============+==========+===============+==============+
| Xapian         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Sphinx         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Hyper Estraier | Yes                    | Yes                 | Yes            | No         | No       | No            | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
