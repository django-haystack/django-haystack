.. _ref-boost:

=====
Boost
=====


Scoring is a critical component of good search. Normal full-text searches
automatically score a document based on how well it matches the query provided.
However, sometimes you want certain documents to score better than they
otherwise would. Boosting is a way to achieve this. There are three types of
boost:

* Term Boost
* Document Boost
* Field Boost

.. note::

    Document & Field boost support was added in Haystack 1.1.

Despite all being types of boost, they take place at different times and have
slightly different effects on scoring.

Term boost happens at query time (when the search query is run) and is based
around increasing the score if a certain word/phrase is seen.

On the other hand, document & field boosts take place at indexing time (when
the document is being added to the index). Document boost causes the relevance
of the entire result to go up, where field boost causes only searches within
that field to do better.

.. warning::

  Be warned that boost is very, very sensitive & can hurt overall search
  quality if over-zealously applied. Even very small adjustments can affect
  relevance in a big way.

Term Boost
==========

Term boosting is achieved by using ``SearchQuerySet.boost``. You provide it
the term you want to boost on & a floating point value (based around ``1.0``
as 100% - no boost).

Example::

    # Slight increase in relevance for documents that include "banana".
    sqs = SearchQuerySet().boost('banana', 1.1)

    # Big decrease in relevance for documents that include "blueberry".
    sqs = SearchQuerySet().boost('blueberry', 0.8)

See the :doc:`searchqueryset_api` docs for more details on using this method.


Document Boost
==============

Document boosting is done by adding a ``boost`` field to the prepared data
``SearchIndex`` creates. The best way to do this is to override
``SearchIndex.prepare``::

    from haystack import indexes
    from notes.models import Note


    class NoteSearchIndex(indexes.SearchIndex, indexes.Indexable):
        # Your regular fields here then...

        def prepare(self, obj):
            data = super(NoteSearchIndex, self).prepare(obj)
            data['boost'] = 1.1
            return data


Another approach might be to add a new field called ``boost``. However, this
can skew your schema and is not encouraged.


Field Boost
===========

Field boosting is enabled by setting the ``boost`` kwarg on the desired field.
An example of this might be increasing the significance of a ``title``::

    from haystack import indexes
    from notes.models import Note


    class NoteSearchIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        title = indexes.CharField(model_attr='title', boost=1.125)

        def get_model(self):
            return Note

.. note::

  Field boosting only has an effect when the SearchQuerySet filters on the
  field which has been boosted. If you are using a default search view or
  form you will need override the search method or other include the field
  in your search query. This example CustomSearchForm searches the automatic
  ``content`` field and the ``title`` field which has been boosted::

    from haystack.forms import SearchForm

    class CustomSearchForm(SearchForm):

        def search(self):
            if not self.is_valid():
                return self.no_query_found()

            if not self.cleaned_data.get('q'):
                return self.no_query_found()

            q = self.cleaned_data['q']
            sqs = self.searchqueryset.filter(SQ(content=AutoQuery(q)) | SQ(title=AutoQuery(q)))

            if self.load_all:
                sqs = sqs.load_all()

            return sqs.highlight()
