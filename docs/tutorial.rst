=====================
Djangosearch Tutorial
=====================

May need to include some bits about setting up Solr. Provide a base blog app
example (models).


1. Add Djangosearch To INSTALLED_APPS
-------------------------------------

In ```settings.py```, add ```djangosearch``` to INSTALLED_APPS.


3. Create ModelIndexes
----------------------


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

