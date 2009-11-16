.. _ref-searchfield-api:

===================
``SearchField`` API
===================

.. class:: SearchField

The ``SearchField`` and it's subclasses provides a way to declare what data
you're interested in indexing. They are used with ``SearchIndexes``, much like
``forms.*Field`` are used within forms or ``models.*Field`` within models.

They provide both the means for storing data in the index, as well as preparing
the data before it's placed in the index.

In practice, you'll likely never actually use the base ``SearchField``, as the
subclasses are much better at handling real data.


Subclasses
==========

Included with Haystack are the following field types:

* ``CharField``
* ``IntegerField``
* ``FloatField``
* ``BooleanField``
* ``DateField``
* ``DateTimeField``
* ``MultiValueField``


Usage
=====

While ``SearchField`` objects can be used on their own, they're generally used
within a ``SearchIndex``. You use them in a declarative manner, just like
fields in ``django.forms.Form`` or ``django.db.models.Model`` objects. For
example::

    from haystack import indexes
    
    
    class NoteIndex(indexes.SearchIndex):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')

This will hook up those fields with the index and, when updating a ``Model``
object, pull the relevant data out and prepare it for storage in the index.


Method Reference
================

``__init__``
~~~~~~~~~~~~

.. method:: SearchField.__init__(self, model_attr=None, use_template=False, template_name=None, document=False, indexed=True, stored=True, default=NOT_PROVIDED, null=False)

Instantiates a fresh ``SearchField`` instance.

``has_default``
~~~~~~~~~~~~~~~

.. method:: SearchField.has_default(self)

Returns a boolean of whether this field has a default value.

``prepare``
~~~~~~~~~~~

.. method:: SearchField.prepare(self, obj)

Takes data from the provided object and prepares it for storage in the
index.

``prepare_template``
~~~~~~~~~~~~~~~~~~~~

.. method:: SearchField.prepare_template(self, obj)

Flattens an object for indexing.

This loads a template
(``search/indexes/{app_label}/{model_name}_{field_name}.txt``) and
returns the result of rendering that template. ``object`` will be in
its context.

``convert``
~~~~~~~~~~~~~~~

.. method:: SearchField.convert(self, value)

Handles conversion between the data found and the type of the field.

Extending classes should override this method and provide correct
data coercion.
