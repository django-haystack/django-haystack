=====================
Djangosearch Tutorial
=====================

May need to include some bits about setting up Solr.

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

1. Add Djangosearch To INSTALLED_APPS
-------------------------------------

In ``settings.py``, add ``djangosearch`` to INSTALLED_APPS.


2. Create An IndexSite
----------------------

Within your URLconf, add the following code::

    import djangosearch
    
    djangosearch.autodiscover()

This will create a default ``IndexSite`` instance, search through all of your
INSTALLED_APPS for ``indexes.py`` and register all ``ModelIndexes`` with the
default ``IndexSite``.

If autodiscovery and inclusion of all indexes is not desirable, you can manually
register models in the following manner::

    from djangosearch.sites import site
    
    site.register(Note)

This registers the model with the default site built into ``djangosearch``. The
model gets registered with a standard ``ModelIndex`` class. If you need to override
this class and provide additional functionality, you can manually register your
own indexes like::

    from djangosearch.sites import site
    
    site.register(Note, NoteIndex)

You can also explicitly setup an ``IndexSite`` as follows::

    from blog.indexes import EntryIndex
    from blog.models import Entry
    from djangosearch.sites import IndexSite
    
    mysite = IndexSite()
    mysite.register(Entry, EntryIndex)


3. Creating ModelIndexes
------------------------

Registering indexes in Djangosearch is very similar to registering models
and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to
override the default indexing behavior for your model you can specify your
own ``ModelIndex`` class.  This is useful for ensuring that future-dated
or non-live content is not indexed and searchable.

Our ``Note`` model has a ``pub_date`` field, so let's update our code to
include our own ``ModelIndex`` to exclude indexing future-dated notes::

    from djangosearch.sites import site
    from djangosearch.indexes import ModelIndex
    import datetime
    
    
    class NoteIndex(ModelIndex):
        def get_query_set(self):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
        def should_index(self, obj):
            "Used to determine if incremental indexing of a model should occur."
            return obj.pub_date <= datetime.datetime.now()


    site.register(Note, NoteIndex)

.. _Django admin site: http://docs.djangoproject.com/en/dev/ref/contrib/admin/


4. Add The SearchView To Your URLconf
-------------------------------------

Within your URLconf, add the following line::

    (r'^search/', include('djangosearch.urls')),

This will pull in the default URLconf for djangosearch. It consists of a single
URLconf that points to a SearchView instance. You can change this class's
behavior by passing it any of several keyword arguments or override it entirely
with your own view.


5. Search Template
------------------

Your search template will likely be very simple. The following is enough to
get going (your template/block names will likely differ)::

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

