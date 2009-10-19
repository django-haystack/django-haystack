.. _ref-tutorial:

=================
Haystack Tutorial
=================

We'll be adding search functionality to a simple application.  Here is
``myapp/models.py``::

    from django.db import models
    from django.contrib.auth.models import User


    class Note(models.Model):
        user = models.ForeignKey(User)
        pub_date = models.DateTimeField()
        title = models.CharField(max_length=200)
        body = models.TextField()

        def __unicode__(self):
            return self.title

Initial Setup
-------------

Before starting with Haystack, you will want to choose a search backend to get
started. There is a quick-start guide to :doc:`installing_search_engines`, though you may
want to defer to each engine's official instructions.


1. Add Haystack To ``INSTALLED_APPS``
-------------------------------------

In ``settings.py``, add ``haystack`` to ``INSTALLED_APPS``.


2. Modify Your ``settings.py``
------------------------------

Within your ``settings.py``, you'll need to add a setting to indicate where your
site configuration file will live and which backend to use, as well as other settings for that backend.

``HAYSTACK_SITECONF`` is a required settings and should provide a Python import
path to a file where you keep your ``SearchSite`` configurations in. This will
be explained in the next step, but for now, add the following settings
(substituting your correct information) and create an empty file at that path::

    HAYSTACK_SITECONF = 'myproject.search_sites'

``HAYSTACK_SEARCH_ENGINE`` is a required setting and should be one of the following:

* ``solr``
* ``whoosh``
* ``dummy``

Example::

    HAYSTACK_SEARCH_ENGINE = 'whoosh'

Additionally, backends may require additional information.

Solr
~~~~

Requires setting ``HAYSTACK_SOLR_URL`` to be the URL where your Solr is running at.

Example::

    HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr'
    # ...or for multicore...
    HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr/mysite'


Whoosh
~~~~~~

Requires setting ``HAYSTACK_WHOOSH_PATH`` to the place on your filesystem where the
Whoosh index should be located. Standard warnings about permissions and keeping
it out of a place your webserver may serve documents out of apply.

Example::

    HAYSTACK_WHOOSH_PATH = '/home/whoosh/mysite_index'


Xapian
~~~~~~

First, install the Xapian backend (via
http://github.com/notanumber/xapian-haystack/tree/master) per the instructions
included with the backend.

Requires setting ``HAYSTACK_XAPIAN_PATH`` to the place on your filesystem where the
Xapian index should be located. Standard warnings about permissions and keeping
it out of a place your webserver may serve documents out of apply.

Example::

    HAYSTACK_XAPIAN_PATH = '/home/xapian/mysite_index'


3. Create A ``SearchIndex``
---------------------------

Within the empty file you create corresponding to your ``HAYSTACK_SITECONF``,
add the following code::

    import haystack
    haystack.autodiscover()

This will create a default ``SearchIndex`` instance, search through all of your
INSTALLED_APPS for ``search_indexes.py`` and register all ``SearchIndexes`` with
the default ``SearchIndex``.

If autodiscovery and inclusion of all indexes is not desirable, you can manually
register models in the following manner::

    from haystack import site
    
    site.register(Note)

This registers the model with the default site built into Haystack. The
model gets registered with a standard ``SearchIndex`` class. If you need to override
this class and provide additional functionality, you can manually register your
own indexes like::

    from haystack import site
    
    site.register(Note, NoteIndex)

You can also explicitly setup an ``SearchIndex`` as follows::

    from myapp.indexes import NoteIndex
    from myapp.models import Note
    from haystack.sites import SearchSite
    
    mysite = SearchSite()
    mysite.register(Note, NoteIndex)


4. Creating ``SearchIndexes``
-----------------------------

Registering indexes in Haystack is very similar to registering models
and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to
override the default indexing behavior for your model you can specify your
own ``SearchIndex`` class.  This is useful for ensuring that future-dated
or non-live content is not indexed and searchable.

Our ``Note`` model has a ``pub_date`` field, so let's update our code to
include our own ``SearchIndex`` to exclude indexing future-dated notes::

    import datetime
    from haystack import indexes
    from haystack import site
    from myapp.models import Note
    
    
    class NoteIndex(indexes.SearchIndex):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')
        
        def get_queryset(self):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
    
    site.register(Note, NoteIndex)

Every custom ``SearchIndex`` requires there be one and only one field with
``document=True``. This is the primary field that will get passed to the backend
for indexing. The field needs to have the same fieldname on all ``SearchIndex``
classes.


Additionally, if you provide ``use_template=True`` on any fields, you'll then
need to create a template at ``search/indexes/myapp/note_<fieldname>.txt``. This
allows you to customize the contents of the field in a way that will mean more
to the search engine. A sample template for the ``text`` field might look like::

    {{ object.title }}
    {{ object.user.get_full_name }}
    {{ object.body }}

In addition, you may specify other fields to be populated along with the
document. In this case, we also index the user who authored the document as
well as the date the document was published. The variable you assign the
SearchField to should directly map to the field your search backend is 
expecting. You instantiate most search fields with a parameter that points to
the attribute of the object to populate that field with.

.. note::

    There is nothing special about the ``text`` field name used in all of the
    examples. It could be anything; you could call it ``pink_polka_dot`` and
    it won't matter. It's simply a convention to call it ``text``.

The exception to this is the ``TemplateField`` class.
This take either no arguments or an explicit template name to populate their contents.
You can find more information about them in the ``SearchIndex`` API reference.

.. _Django admin site: http://docs.djangoproject.com/en/dev/ref/contrib/admin/


5. Add The ``SearchView`` To Your URLconf
-----------------------------------------

Within your URLconf, add the following line::

    (r'^search/', include('haystack.urls')),

This will pull in the default URLconf for Haystack. It consists of a single
URLconf that points to a ``SearchView`` instance. You can change this class's
behavior by passing it any of several keyword arguments or override it entirely
with your own view.


6. Search Template
------------------

Your search template (``search/search.html`` for the default case) will likely
be very simple. The following is enough to get going (your template/block names
will likely differ)::

    {% extends 'base.html' %}
    
    {% block content %}
        <h2>Search</h2>
        
        <form method="get" action=".">
            <table>
                {{ form.as_table }}
                <tr>
                    <td>&nbsp;</td>
                    <td>
                        <input type="submit" value="Search">
                    </td>
                </tr>
            </table>
            
            {% if page.object_list %}
                {% for result in page.object_list %}
                    <p>
                        {{ result.object.title }}
                    </p>
                {% endfor %}
            {% else %}
                <p>No results found.</p>
            {% endif %}
        </form>
    {% endblock %}


7. Reindex
----------

Using ``manage.py``, run the ``reindex`` command to index all of your content.


Complete!
---------

If you visit the search section of your site, you should now be able to enter
a search query and (provided your database has data in it) receive search
results back for the query.
