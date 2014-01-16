.. _ref-backend-support:

===============
Backend Support
===============


Supported Backends
==================

* Solr_
* Elasticsearch_
* Whoosh_
* Xapian_

.. _Solr: http://lucene.apache.org/solr/
.. _Elasticsearch: http://elasticsearch.org/
.. _Whoosh: https://bitbucket.org/mchaput/whoosh/
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
* Spatial search
* Requires: pysolr (2.0.13+) & Solr 3.5+

Elasticsearch
-------------

**Complete & included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Faceting (up to 100 facets)
* Stored (non-indexed) fields
* Highlighting
* Spatial search
* Requires: elasticsearch-py 0.4.3+ & Elasticsearch 0.17.7+

Whoosh
------

**Complete & included with Haystack.**

* Full SearchQuerySet support
* Automatic query building
* "More Like This" functionality
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: whoosh (2.0.0+)

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

Backend Support Matrix
======================

+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+---------+
| Backend        | SearchQuerySet Support | Auto Query Building | More Like This | Term Boost | Faceting | Stored Fields | Highlighting | Spatial |
+================+========================+=====================+================+============+==========+===============+==============+=========+
| Solr           | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          | Yes     |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+---------+
| Elasticsearch  | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes          | Yes     |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+---------+
| Whoosh         | Yes                    | Yes                 | Yes            | Yes        | No       | Yes           | Yes          | No      |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+---------+
| Xapian         | Yes                    | Yes                 | Yes            | Yes        | Yes      | Yes           | Yes (plugin) | No      |
+----------------+------------------------+---------------------+----------------+------------+----------+---------------+--------------+---------+


Wishlist
========

The following are search backends that would be nice to have in Haystack but are
licensed in a way that prevents them from being officially bundled. If the
community expresses interest in any of these, there may be future development.

* Riak_
* Lupyne_
* Sphinx_

.. _Riak: http://www.basho.com/
.. _Lupyne: http://code.google.com/p/lupyne/
.. _Sphinx: http://www.sphinxsearch.com/


Sphinx
------

This backend is unlikely to be built. Sphinx is pretty gimpy & doesn't do
blended search results across all models the way the other engines can.
Very limited featureset as well.

* Full SearchQuerySet support
* Automatic query building
* Term Boosting
* Stored (non-indexed) fields
* Highlighting
* Requires: sphinxapi.py (Comes with Sphinx)
