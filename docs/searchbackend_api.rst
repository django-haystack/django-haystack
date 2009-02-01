=================
SearchBackend API
=================

The ``SearchBackend`` class handles interaction directly with the backend. The
search query it performs is usually fed to it from a ``SearchQuery`` class that
has been built for that backend.

This class must be at least partially implemented on a per-backend basis and
is usually accompanied by a ``SearchQuery`` class within the same module.
