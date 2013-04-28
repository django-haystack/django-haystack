========
Haystack
========

:author: Daniel Lindsley
:date: 2013/04/28

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Elasticsearch_, Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Elasticsearch: http://elasticsearch.org/
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
* v1.2.X: http://django-haystack.readthedocs.org/en/v1.2.6/
* v1.1.X: http://django-haystack.readthedocs.org/en/v1.1/


Requirements
============

Haystack has a relatively easily-met set of requirements.

* Python 2.5+
* Django 1.3+

Additionally, each backend has its own requirements. You should refer to
http://docs.haystacksearch.org/dev/installing_search_engines.html for more
details.
