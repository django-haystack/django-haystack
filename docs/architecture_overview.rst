.. _ref-architecture-overview:

=====================
Architecture Overview
=====================

``SearchQuerySet``
------------------

One main implementation.

* Standard API that loosely follows ``QuerySet``
* Handles most queries
* Allows for custom "parsing"/building through API
* Dispatches to ``SearchQuery`` for actual query
* Handles automatically creating a query
* Allows for raw queries to be passed straight to backend.


``SearchQuery``
---------------

Implemented per-backend.

* Method for building the query out of the structured data.
* Method for cleaning a string of reserved characters used by the backend.

Main class provides:

* Methods to add filters/models/order-by/boost/limits to the search.
* Method to perform a raw search.
* Method to get the number of hits.
* Method to return the results provided by the backend (likely not a full list).


``SearchBackend``
-----------------

Implemented per-backend.

* Connects to search engine
* Method for saving new docs to index
* Method for removing docs from index
* Method for performing the actual query


``SearchSite``
--------------

One main implementation.

* Standard API that loosely follows ``django.contrib.admin.sites.AdminSite``
* Handles registering/unregistering models to search on a per-site basis.
* Provides a means of adding custom indexes to a model, like ``ModelAdmins``.


``SearchIndex``
---------------

Implemented per-model you wish to index.

* Handles generating the document to be indexed.
* Populates additional fields to accompany the document.
* Provides a way to limit what types of objects get indexed.
* Provides a way to index the document(s).
* Provides a way to remove the document(s).
