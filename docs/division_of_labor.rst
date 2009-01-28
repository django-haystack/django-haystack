Division of Labor
=================

SearchQuerySet
--------------

One main implementation.

* Standard API that loosely follows QuerySet
* Handles most queries
* Allows for custom "parsing"/building through API
* Dispatches to backend for actual query
* Handles automatically creating a query


SearchBackend
-------------

Implemented per-backend.

* Connects to search engine
* Method for saving new docs to index
* Method for removing docs from index
* Method for performing the actual query

  * What does this return? SearchResult objects? A list of dicts?
  * What about the total count?
