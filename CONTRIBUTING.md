Contributing
============

Haystack is open-source and, as such, grows (or shrinks) & improves in part
due to the community. Below are some guidelines on how to help with the project.


Philosophy
----------

* Haystack is BSD-licensed. All contributed code must be either
  * the original work of the author, contributed under the BSD, or...
  * work taken from another project released under a BSD-compatible license.
* GPL'd (or similar) works are not eligible for inclusion.
* Haystack's git master branch should always be stable, production-ready &
  passing all tests.
* Major releases (1.x.x) are commitments to backward-compatibility of the public APIs.
  Any documented API should ideally not change between major releases.
  The exclusion to this rule is in the event of either a security issue
  or to accommodate changes in Django itself.
* Minor releases (x.3.x) are for the addition of substantial features or major
  bugfixes.
* Patch releases (x.x.4) are for minor features or bugfixes.


Guidelines For Reporting An Issue/Feature
-----------------------------------------

So you've found a bug or have a great idea for a feature. Here's the steps you
should take to help get it added/fixed in Haystack:

* First, check to see if there's an existing issue/pull request for the
  bug/feature. All issues are at https://github.com/toastdriven/django-haystack/issues
  and pull reqs are at https://github.com/toastdriven/django-haystack/pulls.
* If there isn't one there, please file an issue. The ideal report includes:
    * A description of the problem/suggestion.
    * How to recreate the bug.
    * If relevant, including the versions of your:
        * Python interpreter
        * Django
        * Haystack
        * Search engine used (as well as bindings)
        * Optionally of the other dependencies involved
* Ideally, creating a pull request with a (failing) test case demonstrating
  what's wrong. This makes it easy for us to reproduce & fix the problem.

  Github has a great guide for writing an effective pull request:
  https://github.com/blog/1943-how-to-write-the-perfect-pull-request

  Instructions for running the tests are at
  https://django-haystack.readthedocs.io/en/latest/running_tests.html

You might also hop into the IRC channel (`#haystack` on `irc.freenode.net`)
& raise your question there, as there may be someone who can help you with a
work-around.


Guidelines For Contributing Code
--------------------------------

If you're ready to take the plunge & contribute back some code/docs, the
process should look like:

* Fork the project on GitHub into your own account.
* Clone your copy of Haystack.
* Make a new branch in git & commit your changes there.
* Push your new branch up to GitHub.
* Again, ensure there isn't already an issue or pull request out there on it.
  If there is & you feel you have a better fix, please take note of the issue
  number & mention it in your pull request.
* Create a new pull request (based on your branch), including what the
  problem/feature is, versions of your software & referencing any related
  issues/pull requests.

In order to be merged into Haystack, contributions must have the following:

* A solid patch that:
    * is clear.
    * works across all supported versions of Python/Django.
    * follows the existing style of the code base (mostly PEP-8).
    * comments included as needed to explain why the code functions as it does
* A test case that demonstrates the previous flaw that now passes
  with the included patch.
* If it adds/changes a public API, it must also include documentation
  for those changes.
* Must be appropriately licensed (see [Philosophy](#philosophy)).
* Adds yourself to the AUTHORS file.

If your contribution lacks any of these things, they will have to be added
by a core contributor before being merged into Haystack proper, which may take
substantial time for the all-volunteer team to get to.
