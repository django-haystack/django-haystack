.. _ref-templatetags:

=============
Template Tags
=============

Haystack comes with a couple common template tags to make using some of its
special features available to templates.


``highlight``
=============

Takes a block of text and highlights words from a provided query within that
block of text. Optionally accepts arguments to provide the HTML tag to wrap 
highlighted word in, a CSS class to use with the tag and a maximum length of
the blurb in characters.

The defaults are ``span`` for the HTML tag, ``highlighted`` for the CSS class
and 200 characters for the excerpt.

Syntax::

    {% highlight <text_block> with <query> [css_class "class_name"] [html_tag "span"] [max_length 200] %}

Example::

    # Highlight summary with default behavior.
    {% highlight result.summary with query %}
    
    # Highlight summary but wrap highlighted words with a div and the
    # following CSS class.
    {% highlight result.summary with query html_tag "div" css_class "highlight_me_please" %}
    
    # Highlight summary but only show 40 words.
    {% highlight result.summary with query max_length 40 %}

The highlighter used by this tag can be overridden as needed. See the
:doc:`highlighting` documentation for more information.


``more_like_this``
==================

Fetches similar items from the search index to find content that is similar
to the provided model's content.

.. note::

    This requires a backend that has More Like This built-in.

Syntax::

    {% more_like_this model_instance as varname [for app_label.model_name,app_label.model_name,...] [limit n] %}

Example::

    # Pull a full SearchQuerySet (lazy loaded) of similar content.
    {% more_like_this entry as related_content %}
    
    # Pull just the top 5 similar pieces of content.
    {% more_like_this entry as related_content limit 5  %}
    
    # Pull just the top 5 similar entries or comments.
    {% more_like_this entry as related_content for "blog.entry,comments.comment" limit 5  %}

This tag behaves exactly like ``SearchQuerySet.more_like_this``, so all notes in
that regard apply here as well.
