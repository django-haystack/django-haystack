.. _ref-tutorial:

=============================
Getting Started with Haystack
=============================

Search is a topic of ever increasing importance. Users increasing rely on search
to separate signal from noise and find what they're looking for quickly. In
addition, search can provide insight into what things are popular (many
searches), what things are difficult to find on the site and ways you can
improve the site better.

To this end, Haystack tries to make integrating custom search as easy as
possible while being flexible/powerful enough to handle more advanced use cases.

Haystack is a reusable app (that is, it relies only on its own code and focuses
on providing just search) that plays nicely with both apps you control as well as
third-party apps (such as ``django.contrib.*``) without having to modify the
sources.

Haystack also does pluggable backends (much like Django's database
layer), so virtually all of the code you write ought to be portable between
whichever search engine you choose.

.. note::

    If you hit a stumbling block, there is both a `mailing list`_ and
    `#haystack on irc.freenode.net`_ to get help.

.. note::

   You can participate in and/or track the development of Haystack by
   subscribing to the `development mailing list`_.

.. _mailing list: http://groups.google.com/group/django-haystack
.. _#haystack on irc.freenode.net: irc://irc.freenode.net/haystack
.. _development mailing list: http://groups.google.com/group/django-haystack-dev

This tutorial assumes that you have a basic familiarity with the various major
parts of Django (models/forms/views/settings/URLconfs) and tailored to the
typical use case. There are shortcuts available as well as hooks for much
more advanced setups, but those will not be covered here.

For example purposes, we'll be adding search functionality to a simple
note-taking application. Here is ``myapp/models.py``::

    from django.db import models
    from django.contrib.auth.models import User


    class Note(models.Model):
        user = models.ForeignKey(User)
        pub_date = models.DateTimeField()
        title = models.CharField(max_length=200)
        body = models.TextField()

        def __unicode__(self):
            return self.title

Finally, before starting with Haystack, you will want to choose a search
backend to get started. There is a quick-start guide to
:doc:`installing_search_engines`, though you may want to defer to each engine's
official instructions.


Installation
=============

Use your favorite Python package manager to install the app from PyPI, e.g.

Example::

    pip install django-haystack


Configuration
=============

Add Haystack To ``INSTALLED_APPS``
----------------------------------

As with most Django applications, you should add Haystack to the
``INSTALLED_APPS`` within your settings file (usually ``settings.py``).

Example::

    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',

        # Added.
        'haystack',

        # Then your usual apps...
        'blog',
    ]


Modify Your ``settings.py``
---------------------------

Within your ``settings.py``, you'll need to add a setting to indicate where your
site configuration file will live and which backend to use, as well as other
settings for that backend.

``HAYSTACK_CONNECTIONS`` is a required setting and should be at least one of
the following:

Solr
~~~~

Example::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://127.0.0.1:8983/solr'
            # ...or for multicore...
            # 'URL': 'http://127.0.0.1:8983/solr/mysite',
        },
    }


Elasticsearch
~~~~~~~~~~~~~

Example::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'haystack',
        },
    }


Whoosh
~~~~~~

Requires setting ``PATH`` to the place on your filesystem where the
Whoosh index should be located. Standard warnings about permissions and keeping
it out of a place your webserver may serve documents out of apply.

Example::

    import os
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
        },
    }


Xapian
~~~~~~

First, install the Xapian backend (via
http://github.com/notanumber/xapian-haystack/tree/master) per the instructions
included with the backend.

Requires setting ``PATH`` to the place on your filesystem where the
Xapian index should be located. Standard warnings about permissions and keeping
it out of a place your webserver may serve documents out of apply.

Example::

    import os
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'xapian_backend.XapianEngine',
            'PATH': os.path.join(os.path.dirname(__file__), 'xapian_index'),
        },
    }


Simple
~~~~~~

The ``simple`` backend using very basic matching via the database itself. It's
not recommended for production use but it will return results.

.. warning::

    This backend does *NOT* work like the other backends do. Data preparation
    does nothing & advanced filtering calls do not work. You really probably
    don't want this unless you're in an environment where you just want to
    silence Haystack.

Example::

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        },
    }


Handling Data
=============

Creating ``SearchIndexes``
--------------------------

``SearchIndex`` objects are the way Haystack determines what data should be
placed in the search index and handles the flow of data in. You can think of
them as being similar to Django ``Models`` or ``Forms`` in that they are
field-based and manipulate/store data.

You generally create a unique ``SearchIndex`` for each type of ``Model`` you
wish to index, though you can reuse the same ``SearchIndex`` between different
models if you take care in doing so and your field names are very standardized.

To build a ``SearchIndex``, all that's necessary is to subclass both
``indexes.SearchIndex`` & ``indexes.Indexable``,
define the fields you want to store data with and define a ``get_model`` method.

We'll create the following ``NoteIndex`` to correspond to our ``Note``
model. This code generally goes in a ``search_indexes.py`` file within the app
it applies to, though that is not required. This allows
Haystack to automatically pick it up. The ``NoteIndex`` should look like::

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
            """Used when the entire index for model is updated."""
            return self.get_model().objects.filter(pub_date__lte=datetime.datetime.now())

Every ``SearchIndex`` requires there be one (and only one) field with
``document=True``. This indicates to both Haystack and the search engine about
which field is the primary field for searching within.

.. warning::

    When you choose a ``document=True`` field, it should be consistently named
    across all of your ``SearchIndex`` classes to avoid confusing the backend.
    The convention is to name this field ``text``.

    There is nothing special about the ``text`` field name used in all of the
    examples. It could be anything; you could call it ``pink_polka_dot`` and
    it won't matter. It's simply a convention to call it ``text``.

Additionally, we're providing ``use_template=True`` on the ``text`` field. This
allows us to use a data template (rather than error-prone concatenation) to
build the document the search engine will index. You’ll need to
create a new template inside your template directory called
``search/indexes/myapp/note_text.txt`` and place the following inside::

    {{ object.title }}
    {{ object.user.get_full_name }}
    {{ object.body }}

In addition, we added several other fields (``author`` and ``pub_date``). These
are useful when you want to provide additional filtering options. Haystack comes
with a variety of ``SearchField`` classes to handle most types of data.

A common theme is to allow admin users to add future content but have it not
display on the site until that future date is reached. We specify a custom
``index_queryset`` method to prevent those future items from being indexed.

.. _Django admin site: http://docs.djangoproject.com/en/dev/ref/contrib/admin/


Setting Up The Views
====================

Add The ``SearchView`` To Your URLconf
--------------------------------------

Within your URLconf, add the following line::

    (r'^search/', include('haystack.urls')),

This will pull in the default URLconf for Haystack. It consists of a single
URLconf that points to a ``SearchView`` instance. You can change this class's
behavior by passing it any of several keyword arguments or override it entirely
with your own view.


Search Template
---------------

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

            {% if query %}
                <h3>Results</h3>

                {% for result in page.object_list %}
                    <p>
                        <a href="{{ result.object.get_absolute_url }}">{{ result.object.title }}</a>
                    </p>
                {% empty %}
                    <p>No results found.</p>
                {% endfor %}

                {% if page.has_previous or page.has_next %}
                    <div>
                        {% if page.has_previous %}<a href="?q={{ query }}&amp;page={{ page.previous_page_number }}">{% endif %}&laquo; Previous{% if page.has_previous %}</a>{% endif %}
                        |
                        {% if page.has_next %}<a href="?q={{ query }}&amp;page={{ page.next_page_number }}">{% endif %}Next &raquo;{% if page.has_next %}</a>{% endif %}
                    </div>
                {% endif %}
            {% else %}
                {# Show some example queries to run, maybe query syntax, something else? #}
            {% endif %}
        </form>
    {% endblock %}

Note that the ``page.object_list`` is actually a list of ``SearchResult``
objects instead of individual models. These objects have all the data returned
from that record within the search index as well as score. They can also
directly access the model for the result via ``{{ result.object }}``. So the
``{{ result.object.title }}`` uses the actual ``Note`` object in the database
and accesses its ``title`` field.


Reindex
-------

The final step, now that you have everything setup, is to put your data in
from your database into the search index. Haystack ships with a management
command to make this process easy.

.. note::

    If you're using the Solr backend, you have an extra step. Solr's
    configuration is XML-based, so you'll need to manually regenerate the
    schema. You should run
    ``./manage.py build_solr_schema`` first, drop the XML output in your
    Solr's ``schema.xml`` file and restart your Solr server.

Simply run ``./manage.py rebuild_index``. You'll get some totals of how many
models were processed and placed in the index.

.. note::

    Using the standard ``SearchIndex``, your search index content is only
    updated whenever you run either ``./manage.py update_index`` or start
    afresh with ``./manage.py rebuild_index``.

    You should cron up a ``./manage.py update_index`` job at whatever interval
    works best for your site (using ``--age=<num_hours>`` reduces the number of
    things to update).

    Alternatively, if you have low traffic and/or your search engine can handle
    it, the ``RealtimeSignalProcessor`` automatically handles updates/deletes
    for you.


Complete!
=========

You can now visit the search section of your site, enter a search query and
receive search results back for the query! Congratulations!


What's Next?
============

This tutorial just scratches the surface of what Haystack provides. The
``SearchQuerySet`` is the underpinning of all search in Haystack and provides
a powerful, ``QuerySet``-like API (see :ref:`ref-searchqueryset-api`). You can
use much more complicated ``SearchForms``/``SearchViews`` to give users a better
UI (see :ref:`ref-views-and_forms`). And the :ref:`ref-best-practices` provides
insight into non-obvious or advanced usages of Haystack.
