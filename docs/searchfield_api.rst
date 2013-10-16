.. _ref-searchfield-api:

===================
``SearchField`` API
===================

.. class:: SearchField

The ``SearchField`` and its subclasses provides a way to declare what data
you're interested in indexing. They are used with ``SearchIndexes``, much like
``forms.*Field`` are used within forms or ``models.*Field`` within models.

They provide both the means for storing data in the index, as well as preparing
the data before it's placed in the index. Haystack uses all fields from all
``SearchIndex`` classes to determine what the engine's index schema ought to
look like.

In practice, you'll likely never actually use the base ``SearchField``, as the
subclasses are much better at handling real data.


Subclasses
==========

Included with Haystack are the following field types:

* ``BooleanField``
* ``CharField``
* ``DateField``
* ``DateTimeField``
* ``DecimalField``
* ``EdgeNgramField``
* ``FloatField``
* ``IntegerField``
* ``LocationField``
* ``MultiValueField``
* ``NgramField``

And equivalent faceted versions:

* ``FacetBooleanField``
* ``FacetCharField``
* ``FacetDateField``
* ``FacetDateTimeField``
* ``FacetDecimalField``
* ``FacetFloatField``
* ``FacetIntegerField``
* ``FacetMultiValueField``

.. note::

  There is no faceted variant of the n-gram fields. Because of how the engine
  generates n-grams, faceting on these field types (``NgramField`` &
  ``EdgeNgram``) would make very little sense.


Usage
=====

While ``SearchField`` objects can be used on their own, they're generally used
within a ``SearchIndex``. You use them in a declarative manner, just like
fields in ``django.forms.Form`` or ``django.db.models.Model`` objects. For
example::

    from haystack import indexes
    from myapp.models import Note


    class NoteIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

This will hook up those fields with the index and, when updating a ``Model``
object, pull the relevant data out and prepare it for storage in the index.


Field Options
=============

``default``
-----------

.. attribute:: SearchField.default

Provides a means for specifying a fallback value in the event that no data is
found for the field. Can be either a value or a callable.

``document``
------------

.. attribute:: SearchField.document

A boolean flag that indicates which of the fields in the ``SearchIndex`` ought
to be the primary field for searching within. Default is ``False``.

.. note::

    Only one field can be marked as the ``document=True`` field, so you should
    standardize this name and the format of the field between all of your
    ``SearchIndex`` classes.

``indexed``
-----------

.. attribute:: SearchField.indexed

A boolean flag for indicating whether or not the data from this field will
be searchable within the index. Default is ``True``.

The companion of this option is ``stored``.

``index_fieldname``
-------------------

.. attribute:: SearchField.index_fieldname

The ``index_fieldname`` option allows you to force the name of the field in the
index. This does not change how Haystack refers to the field. This is useful
when using Solr's dynamic attributes or when integrating with other external
software.

Default is variable name of the field within the ``SearchIndex``.

``model_attr``
--------------

.. attribute:: SearchField.model_attr

The ``model_attr`` option is a shortcut for preparing data. Rather than having
to manually fetch data out of a ``Model``, ``model_attr`` allows you to specify
a string that will automatically pull data out for you. For example::

    # Automatically looks within the model and populates the field with
    # the ``last_name`` attribute.
    author = CharField(model_attr='last_name')

It also handles callables::

    # On a ``User`` object, pulls the full name as pieced together by the
    # ``get_full_name`` method.
    author = CharField(model_attr='get_full_name')

And can look through relations::

    # Pulls the ``bio`` field from a ``UserProfile`` object that has a
    # ``OneToOneField`` relationship to a ``User`` object.
    biography = CharField(model_attr='user__profile__bio')

``null``
--------

.. attribute:: SearchField.null

A boolean flag for indicating whether or not it's permissible for the field
not to contain any data. Default is ``False``.

.. note::

    Unlike Django's database layer, which injects a ``NULL`` into the database
    when a field is marked nullable, ``null=True`` will actually exclude that
    field from being included with the document. This is more efficient for the
    search engine to deal with.

``stored``
----------

.. attribute:: SearchField.stored

A boolean flag for indicating whether or not the data from this field will
be stored within the index. Default is ``True``.

This is useful for pulling data out of the index along with the search result
in order to save on hits to the database.

The companion of this option is ``indexed``.

``template_name``
-----------------

.. attribute:: SearchField.template_name

Allows you to override the name of the template to use when preparing data. By
default, the data templates for fields are located within your ``TEMPLATE_DIRS``
under a path like ``search/indexes/{app_label}/{model_name}_{field_name}.txt``.
This option lets you override that path (though still within ``TEMPLATE_DIRS``).

Example::

    bio = CharField(use_template=True, template_name='myapp/data/bio.txt')

You can also provide a list of templates, as ``loader.select_template`` is used
under the hood.

Example::

    bio = CharField(use_template=True, template_name=['myapp/data/bio.txt', 'myapp/bio.txt', 'bio.txt'])


``use_template``
----------------

.. attribute:: SearchField.use_template

A boolean flag for indicating whether or not a field should prepare its data
via a data template or not. Default is False.

Data templates are extremely useful, as they let you easily tie together
different parts of the ``Model`` (and potentially related models). This leads
to better search results with very little effort.



Method Reference
================

``__init__``
------------

.. method:: SearchField.__init__(self, model_attr=None, use_template=False, template_name=None, document=False, indexed=True, stored=True, faceted=False, default=NOT_PROVIDED, null=False, index_fieldname=None, facet_class=None, boost=1.0, weight=None)

Instantiates a fresh ``SearchField`` instance.

``has_default``
---------------

.. method:: SearchField.has_default(self)

Returns a boolean of whether this field has a default value.

``prepare``
-----------

.. method:: SearchField.prepare(self, obj)

Takes data from the provided object and prepares it for storage in the
index.

``prepare_template``
--------------------

.. method:: SearchField.prepare_template(self, obj)

Flattens an object for indexing.

This loads a template
(``search/indexes/{app_label}/{model_name}_{field_name}.txt``) and
returns the result of rendering that template. ``object`` will be in
its context.

``convert``
-----------

.. method:: SearchField.convert(self, value)

Handles conversion between the data found and the type of the field.

Extending classes should override this method and provide correct
data coercion.
