.. _ref-glossary:

========
Glossary
========

Search is a domain full of its own jargon and definitions. As this may be an
unfamiliar territory to many developers, what follows are some commonly used
terms and what they mean.


Engine
  An engine, for the purposes of Haystack, is a third-party search solution.
  It might be a full service (i.e. Solr_) or a library to build an
  engine with (i.e. Whoosh_)

.. _Solr: http://lucene.apache.org/solr/
.. _Whoosh: https://bitbucket.org/mchaput/whoosh/

Index
  The datastore used by the engine is called an index. Its structure can vary
  wildly between engines but commonly they resemble a document store. This is
  the source of all information in Haystack.

Document
  A document is essentially a record within the index. It usually contains at
  least one blob of text that serves as the primary content the engine searches
  and may have additional data hung off it.

Corpus
  A term for a collection of documents. When talking about the documents stored
  by the engine (rather than the technical implementation of the storage), this
  term is commonly used.

Field
  Within the index, each document may store extra data with the main content as
  a field. Also sometimes called an attribute, this usually represents metadata
  or extra content about the document. Haystack can use these fields for
  filtering and display.

Term
  A term is generally a single word (or word-like) string of characters used
  in a search query.

Stemming
  A means of determining if a word has any root words. This varies by language,
  but in English, this generally consists of removing plurals, an action form of
  the word, et cetera. For instance, in English, 'giraffes' would stem to
  'giraffe'. Similarly, 'exclamation' would stem to 'exclaim'. This is useful
  for finding variants of the word that may appear in other documents.

Boost
  Boost provides a means to take a term or phrase from a search query and alter
  the relevance of a result based on if that term is found in the result, a form
  of weighting. For instance, if you wanted to more heavily weight results that
  included the word 'zebra', you'd specify a boost for that term within the
  query.

More Like This
  Incorporating techniques from information retrieval and artificial
  intelligence, More Like This is a technique for finding other documents within
  the index that closely resemble the document in question. This is useful for
  programmatically generating a list of similar content for a user to browse
  based on the current document they are viewing.

Faceting
  Faceting is a way to provide insight to the user into the contents of your
  corpus. In its simplest form, it is a set of document counts returned with
  results when performing a query. These counts can be used as feedback for
  the user, allowing the user to choose interesting aspects of their search
  results and "drill down" into those results.

  An example might be providing a facet on an ``author`` field, providing back a
  list of authors and the number of documents in the index they wrote. This
  could be presented to the user with a link, allowing the user to click and
  narrow their original search to all results by that author.
