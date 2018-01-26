.. _ref-highlighting:

============
Highlighting
============

Haystack supports two different methods of highlighting. You can either use
``SearchQuerySet.highlight`` or the built-in ``{% highlight %}`` template tag,
which uses the ``Highlighter`` class. Each approach has advantages and
disadvantages you need to weigh when deciding which to use.

If you want portable, flexible, decently fast code, the
``{% highlight %}`` template tag (or manually using the underlying
``Highlighter`` class) is the way to go. On the other hand, if you care more
about speed and will only ever be using one backend,
``SearchQuerySet.highlight`` may suit your needs better.

Use of ``SearchQuerySet.highlight`` is documented in the
:doc:`searchqueryset_api` documentation and the ``{% highlight %}`` tag is
covered in the :doc:`templatetags` documentation, so the rest of this material
will cover the ``Highlighter`` implementation.


``Highlighter``
---------------

The ``Highlighter`` class is a pure-Python implementation included with Haystack
that's designed for flexibility. If you use the ``{% highlight %}`` template
tag, you'll be automatically using this class. You can also use it manually in
your code. For example::

    >>> from haystack.utils.highlighting import Highlighter

    >>> my_text = 'This is a sample block that would be more meaningful in real life.'
    >>> my_query = 'block meaningful'

    >>> highlight = Highlighter(my_query)
    >>> highlight.highlight(my_text)
    u'...<span class="highlighted">block</span> that would be more <span class="highlighted">meaningful</span> in real life.'

The default implementation takes three optional kwargs: ``html_tag``,
``css_class`` and ``max_length``. These allow for basic customizations to the
output, like so::

    >>> from haystack.utils.highlighting import Highlighter

    >>> my_text = 'This is a sample block that would be more meaningful in real life.'
    >>> my_query = 'block meaningful'

    >>> highlight = Highlighter(my_query, html_tag='div', css_class='found', max_length=35)
    >>> highlight.highlight(my_text)
    u'...<div class="found">block</div> that would be more <div class="found">meaningful</div>...'

Further, if this implementation doesn't suit your needs, you can define your own
custom highlighter class. As long as it implements the API you've just seen, it
can highlight however you choose. For example::

    # In ``myapp/utils.py``...
    from haystack.utils.highlighting import Highlighter

    class BorkHighlighter(Highlighter):
        def render_html(self, highlight_locations=None, start_offset=None, end_offset=None):
            highlighted_chunk = self.text_block[start_offset:end_offset]

            for word in self.query_words:
                highlighted_chunk = highlighted_chunk.replace(word, 'Bork!')

            return highlighted_chunk

Then set the ``HAYSTACK_CUSTOM_HIGHLIGHTER`` setting to
``myapp.utils.BorkHighlighter``. Usage would then look like::

    >>> highlight = BorkHighlighter(my_query)
    >>> highlight.highlight(my_text)
    u'Bork! that would be more Bork! in real life.'

Now the ``{% highlight %}`` template tag will also use this highlighter.
