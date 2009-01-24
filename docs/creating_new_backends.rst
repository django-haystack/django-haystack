=====================
Creating New Backends
=====================

The process should be fairly simple.

    # Create new backend file. Name is important.
    # Two classes inside.
        # SearchBackend
        # SearchQuery


SearchBackend
=============

Responsible for the actual connection and low-level details of interacting with
the backend.

    * Connects to search engine
    * Method for saving new docs to index
    * Method for removing docs from index
    * Method for performing the actual query
        * Returns SearchResult objects
        * Must populate a hit count if provided by backend


SearchQuery
===========

Responsible for taking structured data about the query and converting it into a
backend appropriate format.

    * Method for build_query
    * Method for get_count
