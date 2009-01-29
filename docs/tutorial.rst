=====================
Djangosearch Tutorial
=====================

May need to include some bits about setting up Solr. Provide a base blog app
example (models).

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

In ```settings.py```, add ```djangosearch``` to INSTALLED_APPS.


3. Create ModelIndexes
----------------------

The simplest way to index this model is to register it with the default
index site.  Add the following to ``myapp/models.py``::

    from djangosearch.sites import site
    site.register(Note)

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

2. Create An IndexSite
----------------------

Within your URLconf, add the following code::

    import djangosearch
    
    djangosearch.autodiscover()

This will create a default IndexSite instance, search through all of your
INSTALLED_APPS for ```indexes.py``` and register all ModelIndexes with the
default IndexSite.

You can also explicitly setup an IndexSite as follows::

    from blog.indexes import EntryIndex
    from blog.models import Entry
    from djangosearch.sites import IndexSite
    
    mysite = IndexSite()
    mysite.register(Entry, EntryIndex)


4. Add The SearchView To Your URLconf
-------------------------------------


5. Search Template
------------------

