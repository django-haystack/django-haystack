# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import Library, Node, TemplateSyntaxError
from django.utils import six
from django.utils.encoding import smart_str
from django.utils.module_loading import import_string


register = Library()


class HighlightNode(Node):
    """
    Takes a block of text and highlights words from a provided query within that
    block of text. Optionally accepts arguments to provide the HTML tag to wrap
    highlighted word in, a CSS class to use with the tag, a maximum length of
    the blurb in characters, and whether to trim the text being highlighted.

    Syntax::

        {% highlight <text_block> with <query> [css_class="highlighted"] [html_tag="span"] [max_length=200] trim_text=True %}

    Example::

        # Highlight summary with default behavior.
        {% highlight result.summary with request.query %}

        # Highlight summary but wrap highlighted words with a div and the
        # following CSS class.
        {% highlight result.summary request.query html_tag="div" css_class="highlight_me_please" %}

        # Highlight summary but only show 40 characters.
        {% highlight result.summary request.query max_length=40 %}

        # Highlight summary and don't trim any text
        {% highlight result.summary with query trim_text=False %}

    """

    keyword_pattern = re.compile(r'^(?P<key>[\w]+)=(?P<value>.+)$')

    def __init__(self, parser, token):
        bits = token.split_contents()

        tag_name = bits[0]

        calling_error = """'%s' tag was called incorrectly. Expected format:
            '{%% highlight <text_block> with <query> [key_1="value"] %%}.""" % tag_name

        if len(bits) < 4 or bits[2] != 'with':
            raise TemplateSyntaxError(calling_error)

        self.text_block = parser.compile_filter(bits[1])
        self.query = parser.compile_filter(bits[3])
        self.options = {}

        for bit in bits[4:]:
            match = self.keyword_pattern.match(bit)
            if not match:
                raise TemplateSyntaxError(calling_error)
            key = smart_str(match.group('key'))
            value = parser.compile_filter(match.group('value'))
            self.options[key] = value

    def render(self, context):
        text_block = self.text_block.resolve(context)
        query = self.query.resolve(context)
        kwargs = {}

        for key, value in self.options.items():
            noresolve = {'True': True, 'False': False, 'None': None}
            value = noresolve.get(six.text_type(value), value.resolve(context))
            if key == 'options':
                kwargs.update(value)
            else:
                kwargs[key] = value

        # Handle a user-defined highlighting function.
        custom_highlighter = getattr(settings, 'HAYSTACK_CUSTOM_HIGHLIGHTER', None)
        if custom_highlighter:
            try:
                highlighter_class = import_string(custom_highlighter)
            except (ImportError, AttributeError) as e:
                raise ImproperlyConfigured("The highlighter '%s' could not be imported: %s" % (settings.HAYSTACK_CUSTOM_HIGHLIGHTER, e))
        else:
            from haystack.utils import Highlighter
            highlighter_class = Highlighter

        highlighter = highlighter_class(query, **kwargs)
        return highlighter.highlight(text_block)


@register.tag
def highlight(parser, token):
    return HighlightNode(parser, token)
