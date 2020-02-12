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
.. _Whoosh: https://bitbucket.org/mchaput/whoosh/
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

Build Status
============

.. image:: https://travis-ci.org/django-haystack/django-haystack.svg?branch=master
   :target: https://travis-ci.org/django-haystack/django-haystack

Requirements
============

Haystack has a relatively easily-met set of requirements.

* Python 3.5+
* A supported version of Django: https://www.djangoproject.com/download/#supported-versions

Additionally, each backend has its own requirements. You should refer to
https://django-haystack.readthedocs.io/en/latest/installing_search_engines.html for more
details.
