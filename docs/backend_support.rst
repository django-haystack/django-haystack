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
* Requires: elasticsearch-py > 1.0 & Elasticsearch 1.0+ (Elasticsearch 2.X is not supported yet `#1247 <https://github.com/django-haystack/django-haystack/issues/1247>`_)

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
* Backend can be downloaded here: `xapian-haystack <http://github.com/notanumber/xapian-haystack/>`__

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


Unsupported Backends & Alternatives
===================================

If you have a search engine which you would like to see supported in Haystack, the current recommendation is
to develop a plugin following the lead of `xapian-haystack <https://pypi.python.org/pypi/xapian-haystack>`_ so
that project can be developed and tested independently of the core Haystack release schedule.

Sphinx
------

This backend has been requested multiple times over the years but does not yet have a volunteer maintainer. If
you would like to work on it, please contact the Haystack maintainers so your project can be linked here and,
if desired, added to the `django-haystack <https://github.com/django-haystack/>`_ organization on GitHub.

In the meantime, Sphinx users should consider Jorge C. Leitão's
`django-sphinxql <https://github.com/jorgecarleitao/django-sphinxql>`_ project.
