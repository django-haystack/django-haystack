===============
SearchQuery API
===============

The ``SearchQuery`` class acts as an intermediary between ``SearchQuerySet``'s
abstraction and ``SearchBackend``'s actual search. Given the metadata provided
by ``SearchQuerySet``, ``SearchQuery`` build the actual query and interacts
with the ``SearchBackend`` on ``SearchQuerySet``'s behalf.

This class must be at least partially implemented on a per-backend basis, as it
is highly specific to the backend. It usually is bundled with the accompanying
``SearchBackend``.
