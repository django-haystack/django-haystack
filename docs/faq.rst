.. _ref-frequently-asked-questions:

==============================
(In)Frequently Asked Questions
==============================


What is Haystack?
=================

Haystack is meant to be a portable interface to a search engine of your choice.
Some might call it a search framework, an abstraction layer or what have you.
The idea is that you write your search code once and should be able to freely
switch between backends as your situation necessitates.


Why should I consider using Haystack?
=====================================

Haystack is targeted at the following use cases:

* If you want to feature search on your site and search solutions like Google or
  Yahoo search don't fit your needs.
* If you want to be able to customize your search and search on more than just
  the main content.
* If you want to have features like drill-down (faceting) or "More Like This".
* If you want a interface that is non-search engine specific, allowing you to
  change your mind later without much rewriting.


When should I not be using Haystack?
====================================

* Non-Model-based data. If you just want to index random data (flat files,
  alternate sources, etc.), Haystack isn't a good solution. Haystack is very 
  ``Model``-based and doesn't work well outside of that use case.
* Ultra-high volume. Because of the very nature of Haystack (abstraction layer),
  there's more overhead involved. This makes it portable, but as with all
  abstraction layers, you lose a little performance. You also can't take full
  advantage of the exact feature-set of your search engine. This is the price
  of pluggable backends.


Why was Haystack created when there are so many other search options?
=====================================================================

The proliferation of search options in Django is a relatively recent development
and is actually one of the reasons for Haystack's existence. There are too
many options that are only partial solutions or are too engine specific.

Further, most use an unfamiliar API and documentation is lacking in most cases.

Haystack is an attempt to unify these efforts into one solution. That's not to
say there should be no alternatives, but Haystack should provide a good
solution to 80%+ of the search use cases out there.


What's the history behind Haystack?
===================================

Haystack started because of my frustration with the lack of good search options
(before many other apps came out) and as the result of extensive use of
Djangosearch. Djangosearch was a decent solution but had a number of
shortcomings, such as:

* Tied to the models.py, so you'd have to modify the source of third-party (
  or django.contrib) apps in order to effectively use it.
* All or nothing approach to indexes. So all indexes appear on all sites and
  in all places.
* Lack of tests.
* Lack of documentation.
* Uneven backend implementations.

The initial idea was to simply fork Djangosearch and improve on these (and
other issues). However, after stepping back, I decided to overhaul the entire
API (and most of the underlying code) to be more representative of what I would
want as an end-user. The result was starting afresh and reusing concepts (and
some code) from Djangosearch as needed.

As a result of this heritage, you can actually still find some portions of
Djangosearch present in Haystack (especially in the ``SearchIndex`` and
``SearchBackend`` classes) where it made sense. The original authors of
Djangosearch are aware of this and thus far have seemed to be fine with this
reuse.


Why doesn't <search engine X> have a backend included in Haystack?
==================================================================

Several possibilities on this.

#. Licensing

   A common problem is that the Python bindings for a specific engine may
   have been released under an incompatible license. The goal is for Haystack
   to remain BSD licensed and importing bindings with an incompatible license
   can technically convert the entire codebase to that license. This most
   commonly occurs with GPL'ed bindings.

#. Lack of time

   The search engine in question may be on the list of backends to add and we
   simply haven't gotten to it yet. We welcome patches for additional backends.

#. Incompatible API

   In order for an engine to work well with Haystack, a certain baseline set of
   features is needed. This is often an issue when the engine doesn't support
   ranged queries or additional attributes associated with a search record.

#. We're not aware of the engine

   If you think we may not be aware of the engine you'd like, please tell us
   about it (preferably via the group - 
   http://groups.google.com/group/django-haystack/). Be sure to check through
   the backends (in case it wasn't documented) and search the history on the
   group to minimize duplicates.
