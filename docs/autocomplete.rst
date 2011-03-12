.. _ref-autocomplete:

============
Autocomplete
============

Autocomplete is becoming increasingly common as an add-on to search. Haystack
makes it relatively simple to implement. There are two steps in the process,
one to prepare the data and one to implement the actual search.

Step 1. Setup The Data
======================

To do autocomplete effectively, the search backend uses n-grams (essential
a small window passed over the string). Because this alters the way your
data needs to be stored, the best approach is to add a new field to your
``SearchIndex`` that contains the text you want to autocomplete on.

You have two choices: ``NgramField`` & ``EdgeNgramField``. Though very similar,
the choice of field is somewhat important.

* If you're working with standard text, ``EdgeNgramField`` tokenizes on
  whitespace. This prevents incorrect matches when part of two different words
  are mashed together as one n-gram. **This is what most users should use.**
* If you're working with Asian languages or want to be able to autocomplete
  across word boundaries, ``NgramField`` should be what you use.

Example (continuing from the tutorial)::

    import datetime
    from haystack import indexes
    from haystack import site
    from myapp.models import Note
    
    
    class NoteIndex(indexes.SearchIndex):
        text = indexes.CharField(document=True, use_template=True)
        author = indexes.CharField(model_attr='user')
        pub_date = indexes.DateTimeField(model_attr='pub_date')
        # We add this for autocomplete.
        content_auto = indexes.EdgeNgramField(model_attr='content')
        
        def get_queryset(self):
            """Used when the entire index for model is updated."""
            return Note.objects.filter(pub_date__lte=datetime.datetime.now())
    
    
    site.register(Note, NoteIndex)

As with all schema changes, you'll need to rebuild/update your index after
making this change.


Step 2. Performing The Query
============================

Haystack ships with a convenience method to perform most autocomplete searches.
You simply provide a field & the query you wish to search on to the
``SearchQuerySet.autocomplete`` method. Given the previous example, an example
search would look like::

    from haystack.query import SearchQuerySet
    
    SearchQuerySet().autocomplete(content_auto='old')
    # Result match things like 'goldfish', 'cuckold' & 'older'.

The results from the ``SearchQuerySet.autocomplete`` method are full search
results, just like any regular filter.

If you need more control over your results, you can use standard
``SearchQuerySet.filter`` calls. For instance::

    from haystack.query import SearchQuerySet
    
    sqs = SearchQuerySet().filter(content_auto=request.GET.get('q', ''))

This can also be extended to use ``SQ`` for more complex queries (and is what's
being done under the hood in the ``SearchQuerySet.autocomplete`` method).
