.. _ref-other_apps:

=============================
Haystack-Related Applications
=============================

Sub Apps
========

These are apps that build on top of the infrastructure provided by Haystack.
Useful for essentially extending what Haystack can do.

queued_search
-------------

http://github.com/toastdriven/queued_search (2.X compatible)

Provides a queue-based setup as an alternative to ``RealtimeSignalProcessor`` or
constantly running the ``update_index`` command. Useful for high-load, short
update time situations.

celery-haystack
---------------

https://github.com/jezdez/celery-haystack (1.X and 2.X compatible)

Also provides a queue-based setup, this time centered around Celery. Useful
for keeping the index fresh per model instance or with the included task
to call the ``update_index`` management command instead.

haystack-rqueue
---------------

https://github.com/mandx/haystack-rqueue (2.X compatible)

Also provides a queue-based setup, this time centered around RQ. Useful
for keeping the index fresh using ``./manage.py rqworker``.

django-celery-haystack
----------------------

https://github.com/mixcloud/django-celery-haystack-SearchIndex

Another queue-based setup, also around Celery. Useful
for keeping the index fresh.

saved_searches
--------------

http://github.com/toastdriven/saved_searches (2.X compatible)

Adds personalization to search. Retains a history of queries run by the various
users on the site (including anonymous users). This can be used to present the
user with their search history and provide most popular/most recent queries
on the site.

saved-search
------------

https://github.com/DirectEmployers/saved-search

An alternate take on persisting user searches, this has a stronger focus
on locale-based searches as well as further integration.

haystack-static-pages
---------------------

http://github.com/trapeze/haystack-static-pages

Provides a simple way to index flat (non-model-based) content on your site.
By using the management command that comes with it, it can crawl all pertinent
pages on your site and add them to search.

django-tumbleweed
-----------------

http://github.com/mcroydon/django-tumbleweed

Provides a tumblelog-like view to any/all Haystack-enabled models on your
site. Useful for presenting date-based views of search data. Attempts to avoid
the database completely where possible.


Haystack-Enabled Apps
=====================

These are reusable apps that ship with ``SearchIndexes``, suitable for quick
integration with Haystack.

* django-faq (freq. asked questions app) - http://github.com/benspaulding/django-faq
* django-essays (blog-like essay app) - http://github.com/bkeating/django-essays
* gtalug (variety of apps) - http://github.com/myles/gtalug
* sciencemuseum (science museum open data) - http://github.com/simonw/sciencemuseum
* vz-wiki (wiki) - http://github.com/jobscry/vz-wiki
* ffmff (events app) - http://github.com/stefreak/ffmff
* Dinette (forums app) - http://github.com/uswaretech/Dinette
* fiftystates_site (site) - http://github.com/sunlightlabs/fiftystates_site
* Open-Knesset (site) - http://github.com/ofri/Open-Knesset
