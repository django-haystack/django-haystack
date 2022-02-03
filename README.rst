.. image:: https://github.com/django-haystack/django-haystack/actions/workflows/test.yml/badge.svg
      :target: https://github.com/django-haystack/django-haystack/actions/workflows/test.yml
.. image:: https://img.shields.io/pypi/v/django-haystack.svg
      :target: https://pypi.python.org/pypi/django-haystack/
.. image:: https://img.shields.io/pypi/pyversions/django-haystack.svg
      :target: https://pypi.python.org/pypi/django-haystack/
.. image:: https://img.shields.io/pypi/dm/django-haystack.svg
      :target: https://pypi.python.org/pypi/django-haystack/
.. image:: https://readthedocs.org/projects/django-haystack/badge/
      :target: https://django-haystack.readthedocs.io/
.. image:: https://img.shields.io/badge/code%20style-black-000.svg
      :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
      :target: https://pycqa.github.io/isort/

========
Haystack
========

:author: Daniel Lindsley
:date: 2013/07/28

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Elasticsearch_, Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Elasticsearch: https://www.elastic.co/products/elasticsearch
.. _Whoosh: https://github.com/mchaput/whoosh/
.. _Xapian: http://xapian.org/

Haystack is BSD licensed, plays nicely with third-party app without needing to
modify the source and supports advanced features like faceting, More Like This,
highlighting, spatial search and spelling suggestions.

You can find more information at http://haystacksearch.org/.


Getting Help
============

There is a mailing list (http://groups.google.com/group/django-haystack/)
available for general discussion and an IRC channel (#haystack on
irc.freenode.net).


Documentation
=============

* Development version: http://docs.haystacksearch.org/
* v2.8.X: https://django-haystack.readthedocs.io/en/v2.8.1/
* v2.7.X: https://django-haystack.readthedocs.io/en/v2.7.0/
* v2.6.X: https://django-haystack.readthedocs.io/en/v2.6.0/

See the `changelog <docs/changelog.rst>`_

Requirements
============

Haystack has a relatively easily-met set of requirements.

* Python 3.6+
* A supported version of Django: https://www.djangoproject.com/download/#supported-versions

Additionally, each backend has its own requirements. You should refer to
https://django-haystack.readthedocs.io/en/latest/installing_search_engines.html for more
details.
