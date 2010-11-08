.. _ref-backend-support:

===============
Backend Support
===============


Supported Backends
==================

* Solr_
* Whoosh_
* Xapian_

.. _Solr: http://lucene.apache.org/solr/
.. _Whoosh: http://whoosh.ca/
.. _Xapian: http://xapian.org/


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
* Requires: pysolr (2.0.13+) & Solr 1.3+

Whoosh
------

**Complete & included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: whoosh (1.1.1+)

Xapian
------

**Complete & available as a third-party download.**

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Faceting
* Stored (non-indexed) fields
* Highlighting
* Requires: Xapian 1.0.5+ & python-xapian 1.0.5+
* Backend can be downloaded here: `xapian-haystack <http://github.com/notanumber/xapian-haystack/>`_


+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields | Highlighting |
+================+========================+=====================+================+============+==========+===============+==============+
| Solr           | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Whoosh         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Xapian         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+


Wishlist
========

The following are search backends that would be nice to have in Haystack but are
licensed in a way that prevents them from being officially bundled. If the
community expresses interest in any of these, there may be future development.

* Sphinx_
* `Hyper Estraier`_

.. _Sphinx: http://www.sphinxsearch.com/
.. _Hyper Estraier: http://hyperestraier.sourceforge.net/


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
| Sphinx         | Yes                    | Yes                 | No             | Yes        | No       | Yes           | Yes          |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
| Hyper Estraier | Yes                    | Yes                 | Yes            | No         | No       | No            | Yes (plugin) |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+
