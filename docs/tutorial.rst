=====================
Haystack Tutorial
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

1. Add Haystack To INSTALLED_APPS
-------------------------------------

In ``settings.py``, add ``haystack`` to INSTALLED_APPS.


2. Create An SearchIndex
------------------------

Within your URLconf, add the following code::

    import haystack
    
    haystack.autodiscover()

This will create a default ``SearchIndex`` instance, search through all of your
INSTALLED_APPS for ``indexes.py`` and register all ``ModelIndexes`` with the
default ``SearchIndex``.

If autodiscovery and inclusion of all indexes is not desirable, you can manually
register models in the following manner::

    from haystack.sites import site
    
    site.register(Note)

This registers the model with the default site built into ``haystack``. The
model gets registered with a standard ``ModelIndex`` class. If you need to override
this class and provide additional functionality, you can manually register your
own indexes like::

    from haystack.sites import site
    
    site.register(Note, NoteIndex)

You can also explicitly setup an ``SearchIndex`` as follows::

    from myapp.indexes import NoteIndex
    from myapp.models import Note
    from haystack.sites import SearchIndex
    
    mysite = SearchIndex()
    mysite.register(Note, NoteIndex)


3. Creating ModelIndexes
------------------------

Registering indexes in Haystack is very similar to registering models
and ``ModelAdmin`` classes in the `Django admin site`_.  If you want to
override the default indexing behavior for your model you can specify your
own ``ModelIndex`` class.  This is useful for ensuring that future-dated
or non-live content is not indexed and searchable.

Our ``Note`` model has a ``pub_date`` field, so let's update our code to
include our own ``ModelIndex`` to exclude indexing future-dated notes::

    import datetime
    from haystack import indexes
    from haystack.sites import site
    from myapp.models import Note
    
    
    class NoteIndex(indexes.ModelIndex):
        text = indexes.ContentField()
        author = indexes.CharField('user')
        pub_date = indexes.DateTimeField('pub_date')
        
        def get_query_set(self):
            "Used when the entire index for model is updated."
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
    
    site.register(Note, NoteIndex)

Every custom ``ModelIndex`` requires there be one and only one ContentField.
This is the primary field that will get passed to the backend for indexing. For
this field, you'll then need to create a template at 
``search/indexes/myapp/note.txt``. This allows you to customize the document 
that will be passed to the search backend for indexing. A sample template
might look like::

    {{ object.title }}
    Written by {{ object.user.full_name }}
    
    {{ object.body }}

In addition, you may specify other fields to be populated along with the
document. In this case, we also index the user who authored the document as
well as the date the document was published. The variable you assign the
SearchField to should directly map to the field your search backend is 
expecting. You instantiate most search fields with a parameter that points to
the attribute of the object to populate that field with.

The exception to this are the ``ContentField`` and ``StoredField`` classes.
These take no arguments as they both use templates to populate their contents.
You can find more information about them in the ``ModelIndex`` API reference.

.. _Django admin site: http://docs.djangoproject.com/en/dev/ref/contrib/admin/


4. Add The SearchView To Your URLconf
-------------------------------------

Within your URLconf, add the following line::

    (r'^search/', include('haystack.urls')),

This will pull in the default URLconf for haystack. It consists of a single
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

