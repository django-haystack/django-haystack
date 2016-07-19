# encoding: utf-8

# Python Imports
from __future__ import absolute_import, unicode_literals

# Django Imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import Library
from django.utils.module_loading import import_string

# Haystack Imports
from ..utils import Highlighter


register = Library()


@register.simple_tag
def highlight(text_block, query, **kwargs):
    """
    Takes a block of text and highlights words from a provided query within that
    block of text. Optionally accepts arguments to provide the HTML tag to wrap
    highlighted word in, a CSS class to use with the tag, a maximum length of
    the blurb in characters, and whether to trim the text being highlighted.

    Syntax::

        {% highlight <text_block> <query> [css_class="highlighted"] [html_tag="span"] [max_window=0] [trim=True] %}

    Example::

        # Highlight summary with default behavior.
        {% highlight result.summary request.query %}

        # Highlight summary but wrap highlighted words with a div and the following CSS class.
        {% highlight result.summary request.query html_tag="div" css_class="highlight_me_please" %}

        # Highlight summary but only show 40 characters.
        {% highlight result.summary request.query max_window=40 %}

        # Highlight summary and don't trim any text
        {% highlight result.summary query trim=False %}

    """

    # Handle a user-defined highlighting function.
    custom_highlighter = getattr(settings, 'HAYSTACK_CUSTOM_HIGHLIGHTER', None)
    if custom_highlighter:
        try:
            highlighter_class = import_string(custom_highlighter)
        except (ImportError, AttributeError) as e:
            raise ImproperlyConfigured("The highlighter '%s' could not be imported: %s" % (settings.HAYSTACK_CUSTOM_HIGHLIGHTER, e))
    else:
        highlighter_class = Highlighter

    highlighter = highlighter_class(query, **kwargs)
    return highlighter.highlight(text_block)
