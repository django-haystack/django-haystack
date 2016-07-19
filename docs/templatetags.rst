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
highlighted word in, a CSS class to use with the tag, the maximum window of
characters in the blurb to highlight, whether to trim the blurb to the window
of highlighted text, and the minimum length of the query that can be highlighted.

The defaults are:
    css_class: ``highlighted``
    html_tag: ``span``
    max_window: ``0`` (will default to length of text block passed)
    trim: ``True``
    min_query_length: ``4``

Syntax::

    {% highlight <text_block> <query> [css_class="highlighted"] [html_tag="span"] [max_window=200] [trim=True] [min_query_length=4] %}

Example::

    # In these examples, the template_context will have the following values:
    # result.summary -> 'This is a sample block that would be more meaningful in real life.'
    # query -> 'block'

    # Highlight summary with default behavior.
    {% highlight result.summary query %}
    -> '...<span class="highlighted">block</span> that would be more meaningful in real life.'
    
    # Highlight summary but wrap highlighted words with a div and the
    # following CSS class.
    {% highlight result.summary query html_tag="div" css_class="highlight_me_please" %}
    -> '...<div class="highlight_me_please">block</div> that would be more meaningful in real life.'
    
    # Highlight summary but only show 40 words.
    {% highlight result.summary query max_window=40 %}
    -> '...<div class="highlight_me_please">block</div> that would be more meaningful in r...'

    # Highlight summary and don't trim any text
    {% highlight result.summary query trim=False %}
    -> 'This is a sample  <div class="highlight_me_please">block</div> that would be more meaningful in real life.'

    # Don't highlight if the query is smaller than the threshold
    {% highlight result.summary 'is' min_query_length=3 %}
    -> 'This is a sample block that would be more meaningful in real life.'

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
