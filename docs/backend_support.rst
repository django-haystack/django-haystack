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

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: pysolr (GitHub version) + Solr 1.3+

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

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: whoosh (0.1.13 w/ included patch or better)


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
* `Hyper Estraier`_
* Sphinx_

.. _Xapian: http://xapian.org/
.. _Hyper Estraier: http://hyperestraier.sourceforge.net/
.. _Sphinx: http://www.sphinxsearch.com/

Xapian
------

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
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
| Xapian         | Yes                    | Yes                 | Yes            | No         | Yes      | Yes           | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Hyper Estraier | Yes                    | Yes                 | Yes            | No         | No       | No            | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Sphinx         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
