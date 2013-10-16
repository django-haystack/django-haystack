.. _ref-views-and_forms:

=============
Views & Forms
=============

Haystack comes with some default, simple views & forms to help you get started
and to cover the common cases. Included is a way to provide:

  * Basic, query-only search.
  * Search by models.
  * Search with basic highlighted results.
  * Faceted search.
  * Search by models with basic highlighted results.

Most processing is done by the forms provided by Haystack via the ``search``
method. As a result, all but the faceted types (see :doc:`faceting`) use the
standard ``SearchView``.

There is very little coupling between the forms & the views (other than relying
on the existence of a ``search`` method on the form), so you may interchangeably
use forms and/or views anywhere within your own code.

Forms
=====

.. currentmodule:: haystack.forms

``SearchForm``
--------------

The most basic of the form types, this form consists of a single field, the
``q`` field (for query). Upon searching, the form will take the cleaned contents
of the ``q`` field and perform an ``auto_query`` on either the custom
``SearchQuerySet`` you provide or off a default ``SearchQuerySet``.

To customize the ``SearchQuerySet`` the form will use, pass it a
``searchqueryset`` parameter to the constructor with the ``SearchQuerySet``
you'd like to use. If using this form in conjunction with a ``SearchView``,
the form will receive whatever ``SearchQuerySet`` you provide to the view with
no additional work needed.

The ``SearchForm`` also accepts a ``load_all`` parameter (``True`` or
``False``), which determines how the database is queried when iterating through
the results. This also is received automatically from the ``SearchView``.

All other forms in Haystack inherit (either directly or indirectly) from this
form.

``HighlightedSearchForm``
-------------------------

Identical to the ``SearchForm`` except that it tags the ``highlight`` method on
to the end of the ``SearchQuerySet`` to enable highlighted results.

``ModelSearchForm``
-------------------

This form adds new fields to form. It iterates through all registered models for
the current ``SearchSite`` and provides a checkbox for each one. If no models
are selected, all types will show up in the results.

``HighlightedModelSearchForm``
------------------------------

Identical to the ``ModelSearchForm`` except that it tags the ``highlight``
method on to the end of the ``SearchQuerySet`` to enable highlighted results on
the selected models.

``FacetedSearchForm``
---------------------

Identical to the ``SearchForm`` except that it adds a hidden ``selected_facets``
field onto the form, allowing the form to narrow the results based on the facets
chosen by the user.

Creating Your Own Form
----------------------

The simplest way to go about creating your own form is to inherit from
``SearchForm`` (or the desired parent) and extend the ``search`` method. By
doing this, you save yourself most of the work of handling data correctly and
stay API compatible with the ``SearchView``.

For example, let's say you're providing search with a user-selectable date range
associated with it. You might create a form that looked as follows::

    from django import forms
    from haystack.forms import SearchForm


    class DateRangeSearchForm(SearchForm):
        start_date = forms.DateField(required=False)
        end_date = forms.DateField(required=False)

        def search(self):
            # First, store the SearchQuerySet received from other processing.
            sqs = super(DateRangeSearchForm, self).search()

            if not self.is_valid():
                return self.no_query_found()

            # Check to see if a start_date was chosen.
            if self.cleaned_data['start_date']:
                sqs = sqs.filter(pub_date__gte=self.cleaned_data['start_date'])

            # Check to see if an end_date was chosen.
            if self.cleaned_data['end_date']:
                sqs = sqs.filter(pub_date__lte=self.cleaned_data['end_date'])

            return sqs

This form adds two new fields for (optionally) choosing the start and end dates.
Within the ``search`` method, we grab the results from the parent form's
processing. Then, if a user has selected a start and/or end date, we apply that
filtering. Finally, we simply return the ``SearchQuerySet``.

Views
=====

.. currentmodule:: haystack.views

Haystack comes bundled with three views, the class-based views (``SearchView`` &
``FacetedSearchView``) and a traditional functional view (``basic_search``).

The class-based views provide for easy extension should you need to alter the
way a view works. Except in the case of faceting (again, see :doc:`faceting`),
the ``SearchView`` works interchangeably with all other forms provided by
Haystack.

The functional view provides an example of how Haystack can be used in more
traditional settings or as an example of how to write a more complex custom
view. It is also thread-safe.

``SearchView(template=None, load_all=True, form_class=None, searchqueryset=None, context_class=RequestContext, results_per_page=None)``
--------------------------------------------------------------------------------------------------------------------------------------------------

The ``SearchView`` is designed to be easy/flexible enough to override common
changes as well as being internally abstracted so that only altering a specific
portion of the code should be easy to do.

Without touching any of the internals of the ``SearchView``, you can modify
which template is used, which form class should be instantiated to search with,
what ``SearchQuerySet`` to use in the event you wish to pre-filter the results.
what ``Context``-style object to use in the response and the ``load_all``
performance optimization to reduce hits on the database. These options can (and
generally should) be overridden at the URLconf level. For example, to have a
custom search limited to the 'John' author, displaying all models to search by
and specifying a custom template (``my/special/path/john_search.html``), your
URLconf should look something like::

    from django.conf.urls.defaults import *
    from haystack.forms import ModelSearchForm
    from haystack.query import SearchQuerySet
    from haystack.views import SearchView

    sqs = SearchQuerySet().filter(author='john')

    # Without threading...
    urlpatterns = patterns('haystack.views',
        url(r'^$', SearchView(
            template='my/special/path/john_search.html',
            searchqueryset=sqs,
            form_class=SearchForm
        ), name='haystack_search'),
    )

    # With threading...
    from haystack.views import SearchView, search_view_factory

    urlpatterns = patterns('haystack.views',
        url(r'^$', search_view_factory(
            view_class=SearchView,
            template='my/special/path/john_search.html',
            searchqueryset=sqs,
            form_class=ModelSearchForm
        ), name='haystack_search'),
    )

.. warning::

    The standard ``SearchView`` is not thread-safe. Use the
    ``search_view_factory`` function, which returns thread-safe instances of
    ``SearchView``.

By default, if you don't specify a ``form_class``, the view will use the
``haystack.forms.ModelSearchForm`` form.

Beyond this customizations, you can create your own ``SearchView`` and
extend/override the following methods to change the functionality.

``__call__(self, request)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generates the actual response to the search.

Relies on internal, overridable methods to construct the response. You generally
should avoid altering this method unless you need to change the flow of the
methods or to add a new method into the processing.

``build_form(self, form_kwargs=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instantiates the form the class should use to process the search query.

Optionally accepts a dictionary of parameters that are passed on to the
form's ``__init__``. You can use this to lightly customize the form.

You should override this if you write a custom form that needs special
parameters for instantiation.

``get_query(self)``
~~~~~~~~~~~~~~~~~~~

Returns the query provided by the user.

Returns an empty string if the query is invalid. This pulls the cleaned query
from the form, via the ``q`` field, for use elsewhere within the ``SearchView``.
This is used to populate the ``query`` context variable.

``get_results(self)``
~~~~~~~~~~~~~~~~~~~~~

Fetches the results via the form.

Returns an empty list if there's no query to search with. This method relies on
the form to do the heavy lifting as much as possible.

``build_page(self)``
~~~~~~~~~~~~~~~~~~~~

Paginates the results appropriately.

In case someone does not want to use Django's built-in pagination, it
should be a simple matter to override this method to do what they would
like.

``extra_context(self)``
~~~~~~~~~~~~~~~~~~~~~~~

Allows the addition of more context variables as needed. Must return a
dictionary whose contents will add to or overwrite the other variables in the
context.

``create_response(self)``
~~~~~~~~~~~~~~~~~~~~~~~~~

Generates the actual HttpResponse to send back to the user. It builds the page,
creates the context and renders the response for all the aforementioned
processing.


``basic_search(request, template='search/search.html', load_all=True, form_class=ModelSearchForm, searchqueryset=None, context_class=RequestContext, extra_context=None, results_per_page=None)``
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The ``basic_search`` tries to provide most of the same functionality as the
class-based views but resembles a more traditional generic view. It's both a
working view if you prefer not to use the class-based views as well as a good
starting point for writing highly custom views.

Since it is all one function, the only means of extension are passing in
kwargs, similar to the way generic views work.


Creating Your Own View
----------------------

As with the forms, inheritance is likely your best bet. In this case, the
``FacetedSearchView`` is a perfect example of how to extend the existing
``SearchView``. The complete code for the ``FacetedSearchView`` looks like::

    class FacetedSearchView(SearchView):
        def extra_context(self):
            extra = super(FacetedSearchView, self).extra_context()

            if self.results == []:
                extra['facets'] = self.form.search().facet_counts()
            else:
                extra['facets'] = self.results.facet_counts()

            return extra

It updates the name of the class (generally for documentation purposes) and
adds the facets from the ``SearchQuerySet`` to the context as the ``facets``
variable. As with the custom form example above, it relies on the parent class
to handle most of the processing and extends that only where needed.
