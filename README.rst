========
Haystack
========

:author: Daniel Lindsley
:date: 2010/03/20

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Whoosh: http://whoosh.ca/
.. _Xapian: http://xapian.org/

Haystack is BSD licensed, plays nicely with third-party app without needing to
modify the source and supports advanced features like faceting, More Like This,
highlighting and spelling suggestions.

You can find more information at http://haystacksearch.org/.


Getting Help
============

There is a mailing list (http://groups.google.com/group/django-haystack/)
available for general discussion and an IRC channel (#haystack on
irc.freenode.net).


Documentation
=============

* Development version: http://docs.haystacksearch.org/dev/
* v1.0: http://docs.haystacksearch.org/1.0/


Requirements
============

Haystack has a relatively easily-met set of requirements.

* Python 2.4+ (may work on 2.3 but untested)
* Django 1.0+

Additionally, each backend has its own requirements. You should refer to
http://docs.haystacksearch.org/dev/installing_search_engines.html for more
details.
