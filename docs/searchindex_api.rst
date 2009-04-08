===============
SearchIndex API
===============

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
    from haystack.sites import site
    from myapp.models import Note
    
    
    class NoteIndex(indexes.SearchIndex):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')
        
        def get_query_set(self):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
    
    site.register(Note, NoteIndex)


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


Significance Of ``document=True``
---------------------------------

Most search engines that were candidates for inclusion in Haystack all had a
central concept of a document that they indexed. These documents form a corpus
within which to primarily search. Because this ideal is so central and most of
Haystack is designed to have pluggable backends, it is important to ensure that
all engines have at least a bare minimum of the data they need to function.

As a result, when creating a ``SeachIndex``, at least one field must be marked
with ``document=True``. This signifies to Haystack that whatever is placed in
this field while indexing is to be the primary text the search engine indexes.
The name of this field can be almost anything, but ``text`` is one of the
more common names used.


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
them though one query instead of many. This still hits the DB and incurs a
performance penalty.

The other option is to leverage stored fields. By default, all fields in
Haystack are both indexed (searchable by the engine) and stored (retained by
the engine and presented in the results). By using a stored field, you can
store commonly used data in such a way that you don't need to hit the database
when processing the search result to get more information.

For example, one great way to leverage this is to pre-rendering an object's
search result template DURING indexing. You define an additional field, render
a template with it and it follows the main indexed record into the index. Then,
when that record is pulled when it matches a query, you can simply display the
contents of that field, which avoids the database hit.::

    # myapp/search_indexes.py
    class MyIndex(indexes.SearchIndex):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')
        # Define the additional field.
        rendered = indexes.CharField(use_template=True, indexed=False)
    
    # templates/search/indexes/myapp/myindex_rendered.txt
    <h2>{{ object.title }}</h2>
    
    <p>{{ object.content }}</p>
    
    # templates/search/search.html
    ...
    
    {% for result in page.object_list %}
        <div class="search_result">
            {{ result.rendered }}
        </div>
    {% endfor %}


Advanced Data Preparation
=========================

Coming soon.


Method Reference
================

``get_query_set(self)``
~~~~~~~~~~~~~~~~~~~~~~~

Get the default QuerySet to index when doing a full update.

Subclasses can override this method to avoid indexing certain objects.

``prepare(self, obj)``
~~~~~~~~~~~~~~~~~~~~~~

Fetches and adds/alters data before indexing.

``get_content_field(self)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the field that supplies the primary document to be indexed.

``update(self)``
~~~~~~~~~~~~~~~~

Update the entire index.

``update_object(self, instance, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Update the index for a single object. Attached to the class's
post-save hook.

``remove_object(self, instance, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Remove an object from the index. Attached to the class's 
post-delete hook.

``clear(self)``
~~~~~~~~~~~~~~~

Clear the entire index.

``reindex(self)``
~~~~~~~~~~~~~~~~~

Completely clear the index for this model and rebuild it.