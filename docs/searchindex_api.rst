.. _ref-searchindex-api:

===================
``SearchIndex`` API
===================

.. class:: SearchIndex()

The ``SearchIndex`` class allows the application developer a way to provide data to
the backend in a structured format. Developers familiar with Django's ``Form``
or ``Model`` classes should find the syntax for indexes familiar.

This class is arguably the most important part of integrating Haystack into your
application, as it has a large impact on the quality of the search results and
how easy it is for users to find what they're looking for. Care and effort
should be put into making your indexes the best they can be.


Quick Start
===========

For the impatient::

    import datetime
    from haystack import indexes
    from myapp.models import Note


    class NoteIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def index_queryset(self, using=None):
            "Used when the entire index for model is updated."
            return self.get_model().objects.filter(pub_date__lte=datetime.datetime.now())


Background
==========

Unlike relational databases, most search engines supported by Haystack are
primarily document-based. They focus on a single text blob which they tokenize,
analyze and index. When searching, this field is usually the primary one that
is searched.

Further, the schema used by most engines is the same for all types of data
added, unlike a relational database that has a table schema for each chunk of
data.

It may be helpful to think of your search index as something closer to a
key-value store instead of imagining it in terms of a RDBMS.


Why Create Fields?
------------------

Despite being primarily document-driven, most search engines also support the
ability to associate other relevant data with the indexed document. These
attributes can be mapped through the use of fields within Haystack.

Common uses include storing pertinent data information, categorizations of the
document, author information and related data. By adding fields for these pieces
of data, you provide a means to further narrow/filter search terms. This can
be useful from either a UI perspective (a better advanced search form) or from a
developer standpoint (section-dependent search, off-loading certain tasks to
search, et cetera).

.. warning::

    Haystack reserves the following field names for internal use: ``id``,
    ``django_ct``, ``django_id`` & ``content``. The ``name`` & ``type`` names
    used to be reserved but no longer are.

    You can override these field names using the ``HAYSTACK_ID_FIELD``,
    ``HAYSTACK_DJANGO_CT_FIELD`` & ``HAYSTACK_DJANGO_ID_FIELD`` if needed.


Significance Of ``document=True``
---------------------------------

Most search engines that were candidates for inclusion in Haystack all had a
central concept of a document that they indexed. These documents form a corpus
within which to primarily search. Because this ideal is so central and most of
Haystack is designed to have pluggable backends, it is important to ensure that
all engines have at least a bare minimum of the data they need to function.

As a result, when creating a ``SearchIndex``, one (and only one) field must be
marked with ``document=True``. This signifies to Haystack that whatever is
placed in this field while indexing is to be the primary text the search engine
indexes. The name of this field can be almost anything, but ``text`` is one of
the more common names used.


Stored/Indexed Fields
---------------------

One shortcoming of the use of search is that you rarely have all or the most
up-to-date information about an object in the index. As a result, when
retrieving search results, you will likely have to access the object in the
database to provide better information.

However, this can also hit the database quite heavily (think
``.get(pk=result.id)`` per object). If your search is popular, this can lead
to a big performance hit. There are two ways to prevent this. The first way is
``SearchQuerySet.load_all``, which tries to group all similar objects and pull
them through one query instead of many. This still hits the DB and incurs a
performance penalty.

The other option is to leverage stored fields. By default, all fields in
Haystack are either indexed (searchable by the engine) or stored (retained by
the engine and presented in the results). By using a stored field, you can
store commonly used data in such a way that you don't need to hit the database
when processing the search result to get more information.

For example, one great way to leverage this is to pre-render an object's
search result template DURING indexing. You define an additional field, render
a template with it and it follows the main indexed record into the index. Then,
when that record is pulled when it matches a query, you can simply display the
contents of that field, which avoids the database hit.:

Within ``myapp/search_indexes.py``::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')
        # Define the additional field.
        rendered = CharField(use_template=True, indexed=False)

Then, inside a template named ``search/indexes/myapp/note_rendered.txt``::

    <h2>{{ object.title }}</h2>

    <p>{{ object.content }}</p>

And finally, in ``search/search.html``::

    ...

    {% for result in page.object_list %}
        <div class="search_result">
            {{ result.rendered|safe }}
        </div>
    {% endfor %}


Keeping The Index Fresh
=======================

There are several approaches to keeping the search index in sync with your
database. None are more correct than the others and which one you use depends
on the traffic you see, the churn rate of your data, and what concerns are
important to you (CPU load, how recent, et cetera).

The conventional method is to use ``SearchIndex`` in combination with cron
jobs. Running a ``./manage.py update_index`` every couple hours will keep your
data in sync within that timeframe and will handle the updates in a very
efficient batch. Additionally, Whoosh (and to a lesser extent Xapian) behaves
better when using this approach.

Another option is to use ``RealtimeSignalProcessor``, which uses Django's
signals to immediately update the index any time a model is saved/deleted. This
yields a much more current search index at the expense of being fairly
inefficient. Solr & Elasticsearch are the only backends that handles this well
under load, and even then, you should make sure you have the server capacity
to spare.

A third option is to develop a custom ``QueuedSignalProcessor`` that, much like
``RealtimeSignalProcessor``, uses Django's signals to enqueue messages for
updates/deletes. Then writing a management command to consume these messages
in batches, yielding a nice compromise between the previous two options.

For more information see :doc:`signal_processors`.

.. note::

    Haystack doesn't ship with a ``QueuedSignalProcessor`` largely because there is
    such a diversity of lightweight queuing options and that they tend to
    polarize developers. Queuing is outside of Haystack's goals (provide good,
    powerful search) and, as such, is left to the developer.

    Additionally, the implementation is relatively trivial & there are already
    good third-party add-ons for Haystack to enable this.


Advanced Data Preparation
=========================

In most cases, using the `model_attr` parameter on your fields allows you to
easily get data from a Django model to the document in your index, as it handles
both direct attribute access as well as callable functions within your model.

.. note::

    The ``model_attr`` keyword argument also can look through relations in
    models. So you can do something like ``model_attr='author__first_name'``
    to pull just the first name of the author, similar to some lookups used
    by Django's ORM.

However, sometimes, even more control over what gets placed in your index is
needed. To facilitate this, ``SearchIndex`` objects have a 'preparation' stage
that populates data just before it is indexed. You can hook into this phase in
several ways.

This should be very familiar to developers who have used Django's ``forms``
before as it loosely follows similar concepts, though the emphasis here is
less on cleansing data from user input and more on making the data friendly
to the search backend.

1. ``prepare_FOO(self, object)``
--------------------------------

The most common way to affect a single field's data is to create a
``prepare_FOO`` method (where FOO is the name of the field). As a parameter
to this method, you will receive the instance that is attempting to be indexed.

.. note::

   This method is analogous to Django's ``Form.clean_FOO`` methods.

To keep with our existing example, one use case might be altering the name
inside the ``author`` field to be "firstname lastname <email>". In this case,
you might write the following code::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def prepare_author(self, obj):
            return "%s <%s>" % (obj.user.get_full_name(), obj.user.email)

This method should return a single value (or list/tuple/dict) to populate that
field's data upon indexing. Note that this method takes priority over whatever
data may come from the field itself.

Just like ``Form.clean_FOO``, the field's ``prepare`` runs before the
``prepare_FOO``, allowing you to access ``self.prepared_data``. For example::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def prepare_author(self, obj):
            # Say we want last name first, the hard way.
            author = u''

            if 'author' in self.prepared_data:
                name_bits = self.prepared_data['author'].split()
                author = "%s, %s" % (name_bits[-1], ' '.join(name_bits[:-1]))

            return author

This method is fully function with ``model_attr``, so if there's no convenient
way to access the data you want, this is an excellent way to prepare it::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        categories = MultiValueField()
        pub_date = DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def prepare_categories(self, obj):
            # Since we're using a M2M relationship with a complex lookup,
            # we can prepare the list here.
            return [category.id for category in obj.category_set.active().order_by('-created')]


2. ``prepare(self, object)``
----------------------------

Each ``SearchIndex`` gets a ``prepare`` method, which handles collecting all
the data. This method should return a dictionary that will be the final data
used by the search backend.

Overriding this method is useful if you need to collect more than one piece
of data or need to incorporate additional data that is not well represented
by a single ``SearchField``. An example might look like::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def prepare(self, object):
            self.prepared_data = super(NoteIndex, self).prepare(object)

            # Add in tags (assuming there's a M2M relationship to Tag on the model).
            # Note that this would NOT get picked up by the automatic
            # schema tools provided by Haystack.
            self.prepared_data['tags'] = [tag.name for tag in object.tags.all()]

            return self.prepared_data

If you choose to use this method, you should make a point to be careful to call
the ``super()`` method before altering the data. Without doing so, you may have
an incomplete set of data populating your indexes.

This method has the final say in all data, overriding both what the fields
provide as well as any ``prepare_FOO`` methods on the class.

.. note::

   This method is roughly analogous to Django's ``Form.full_clean`` and
   ``Form.clean`` methods. However, unlike these methods, it is not fired
   as the result of trying to access ``self.prepared_data``. It requires
   an explicit call.


3. Overriding ``prepare(self, object)`` On Individual ``SearchField`` Objects
-----------------------------------------------------------------------------

The final way to manipulate your data is to implement a custom ``SearchField``
object and write its ``prepare`` method to populate/alter the data any way you
choose. For instance, a (naive) user-created ``GeoPointField`` might look
something like::

    from django.utils import six
    from haystack import indexes

    class GeoPointField(indexes.CharField):
        def __init__(self, **kwargs):
            kwargs['default'] = '0.00-0.00'
            super(GeoPointField, self).__init__(**kwargs)

        def prepare(self, obj):
            return six.text_type("%s-%s" % (obj.latitude, obj.longitude))

The ``prepare`` method simply returns the value to be used for that field. It's
entirely possible to include data that's not directly referenced to the object
here, depending on your needs.

Note that this is NOT a recommended approach to storing geographic data in a
search engine (there is no formal suggestion on this as support is usually
non-existent), merely an example of how to extend existing fields.

.. note::

   This method is analagous to Django's ``Field.clean`` methods.


Adding New Fields
=================

If you have an existing ``SearchIndex`` and you add a new field to it, Haystack
will add this new data on any updates it sees after that point. However, this
will not populate the existing data you already have.

In order for the data to be picked up, you will need to run ``./manage.py
rebuild_index``. This will cause all backends to rebuild the existing data
already present in the quickest and most efficient way.

.. note::

    With the Solr backend, you'll also have to add to the appropriate
    ``schema.xml`` for your configuration before running the ``rebuild_index``.


``Search Index``
================

``get_model``
-------------

.. method:: SearchIndex.get_model(self)

Should return the ``Model`` class (not an instance) that the rest of the
``SearchIndex`` should use.

This method is required & you must override it to return the correct class.

``index_queryset``
------------------

.. method:: SearchIndex.index_queryset(self, using=None)

Get the default QuerySet to index when doing a full update.

Subclasses can override this method to avoid indexing certain objects.

``read_queryset``
-----------------

.. method:: SearchIndex.read_queryset(self, using=None)

Get the default QuerySet for read actions.

Subclasses can override this method to work with other managers.
Useful when working with default managers that filter some objects.

``build_queryset``
-------------------

.. method:: SearchIndex.build_queryset(self, start_date=None, end_date=None)

Get the default QuerySet to index when doing an index update.

Subclasses can override this method to take into account related
model modification times.

The default is to use ``SearchIndex.index_queryset`` and filter
based on ``SearchIndex.get_updated_field``

``prepare``
-----------

.. method:: SearchIndex.prepare(self, obj)

Fetches and adds/alters data before indexing.

``get_content_field``
---------------------

.. method:: SearchIndex.get_content_field(self)

Returns the field that supplies the primary document to be indexed.

``update``
----------

.. method:: SearchIndex.update(self, using=None)

Updates the entire index.

If ``using`` is provided, it specifies which connection should be
used. Default relies on the routers to decide which backend should
be used.

``update_object``
-----------------

.. method:: SearchIndex.update_object(self, instance, using=None, **kwargs)

Update the index for a single object. Attached to the class's
post-save hook.

If ``using`` is provided, it specifies which connection should be
used. Default relies on the routers to decide which backend should
be used.

``remove_object``
-----------------

.. method:: SearchIndex.remove_object(self, instance, using=None, **kwargs)

Remove an object from the index. Attached to the class's
post-delete hook.

If ``using`` is provided, it specifies which connection should be
used. Default relies on the routers to decide which backend should
be used.

``clear``
---------

.. method:: SearchIndex.clear(self, using=None)

Clears the entire index.

If ``using`` is provided, it specifies which connection should be
used. Default relies on the routers to decide which backend should
be used.

``reindex``
-----------

.. method:: SearchIndex.reindex(self, using=None)

Completely clears the index for this model and rebuilds it.

If ``using`` is provided, it specifies which connection should be
used. Default relies on the routers to decide which backend should
be used.

``get_updated_field``
---------------------

.. method:: SearchIndex.get_updated_field(self)

Get the field name that represents the updated date for the model.

If specified, this is used by the reindex command to filter out results
from the ``QuerySet``, enabling you to reindex only recent records. This
method should either return None (reindex everything always) or a
string of the ``Model``'s ``DateField``/``DateTimeField`` name.

``should_update``
-----------------

.. method:: SearchIndex.should_update(self, instance, **kwargs)

Determine if an object should be updated in the index.

It's useful to override this when an object may save frequently and
cause excessive reindexing. You should check conditions on the instance
and return False if it is not to be indexed.

The ``kwargs`` passed along to this method can be the same as the ones passed
by Django when a Model is saved/delete, so it's possible to check if the object
has been created or not. See ``django.db.models.signals.post_save`` for details
on what is passed.

By default, returns True (always reindex).

``load_all_queryset``
---------------------

.. method:: SearchIndex.load_all_queryset(self)

Provides the ability to override how objects get loaded in conjunction
with ``RelatedSearchQuerySet.load_all``. This is useful for post-processing the
results from the query, enabling things like adding ``select_related`` or
filtering certain data.

.. warning::

    Utilizing this functionality can have negative performance implications.
    Please see the section on ``RelatedSearchQuerySet`` within
    :doc:`searchqueryset_api` for further information.

By default, returns ``all()`` on the model's default manager.

Example::

    class NoteIndex(SearchIndex, indexes.Indexable):
        text = CharField(document=True, use_template=True)
        author = CharField(model_attr='user')
        pub_date = DateTimeField(model_attr='pub_date')

        def get_model(self):
            return Note

        def load_all_queryset(self):
            # Pull all objects related to the Note in search results.
            return Note.objects.all().select_related()

When searching, the ``RelatedSearchQuerySet`` appends on a call to ``in_bulk``, so be
sure that the ``QuerySet`` you provide can accommodate this and that the ids
passed to ``in_bulk`` will map to the model in question.

If you need a specific ``QuerySet`` in one place, you can specify this at the
``RelatedSearchQuerySet`` level using the ``load_all_queryset`` method. See
:doc:`searchqueryset_api` for usage.


``ModelSearchIndex``
====================

The ``ModelSearchIndex`` class allows for automatic generation of a
``SearchIndex`` based on the fields of the model assigned to it.

With the exception of the automated introspection, it is a ``SearchIndex``
class, so all notes above pertaining to ``SearchIndexes`` apply. As with the
``ModelForm`` class in Django, it employs an inner class called ``Meta``, which
should contain a ``model`` attribute. By default all non-relational model
fields are included as search fields on the index, but fields can be restricted
by way of a ``fields`` whitelist, or excluded with an ``excludes`` list, to
prevent certain fields from appearing in the class.

In addition, it adds a `text` field that is the ``document=True`` field and
has `use_template=True` option set, just like the ``BasicSearchIndex``.

.. warning::

    Usage of this class might result in inferior ``SearchIndex`` objects, which
    can directly affect your search results. Use this to establish basic
    functionality and move to custom `SearchIndex` objects for better control.

At this time, it does not handle related fields.

Quick Start
-----------

For the impatient::

    import datetime
    from haystack import indexes
    from myapp.models import Note

    # All Fields
    class AllNoteIndex(indexes.ModelSearchIndex, indexes.Indexable):
        class Meta:
            model = Note

    # Blacklisted Fields
    class LimitedNoteIndex(indexes.ModelSearchIndex, indexes.Indexable):
        class Meta:
            model = Note
            excludes = ['user']

    # Whitelisted Fields
    class NoteIndex(indexes.ModelSearchIndex, indexes.Indexable):
        class Meta:
            model = Note
            fields = ['user', 'pub_date']

        # Note that regular ``SearchIndex`` methods apply.
        def index_queryset(self, using=None):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())

