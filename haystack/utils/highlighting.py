# encoding: utf-8

# Python Imports
from __future__ import absolute_import, division, print_function, unicode_literals
import warnings

# Django Imports
from django.utils.html import format_html, mark_safe, strip_tags


class Highlighter(object):
    text_block = ''

    def __init__(self, query, html_tag='span', css_class='highlighted', max_window=200, trim=True, min_query_length=4, **kwargs):
        self.query = query

        self.html_tag = html_tag
        self.css_class = css_class
        self.max_window = int(max_window)
        self.trim = trim
        self.min_query_length = min_query_length

        if 'max_size' in kwargs:
            warnings.warn(('max_size has been deprecated in favor of max_window'), DeprecationWarning)
            self.max_window = int(kwargs['max_size'])

    def highlight(self, text_block):
        text_block = strip_tags(text_block)

        highlight_locations = self.find_highlightable_words(text_block)

        # If no max_window is defined, use the size of the text_block
        max_window = self.max_window or len(text_block)
        start_offset, end_offset = self.find_window(highlight_locations, max_window)

        return self.render_html(text_block, highlight_locations, start_offset, end_offset)

    def extract_query_words(self):
        query = self.query

        if not query:
            return []

        # If the query is an exact-match query, do not split up the words,
        # instead remove the quotes and pass in the whole phrase as the only query word
        if len(query) > 2 and query[0] == query[-1] and query[0] in ["'", '"']:
            words = [query[1:-1].lower()]
        # If not, split up all the words in the query
        else:
            words = set(query.lower().split())

        return [word for word in words if word[0] != '-' and len(word) >= self.min_query_length]

    def find_highlightable_words(self, text_block):
        # Use a set so we only do this once per unique word.
        word_positions = {}

        # Pre-compute the length.
        end_offset = len(text_block)
        lower_text_block = text_block.lower()

        for word in self.extract_query_words():
            selected = word_positions.setdefault(word, [])

            start_offset = 0

            while start_offset < end_offset:
                next_offset = lower_text_block.find(word, start_offset, end_offset)

                # If we get a -1 out of find, it wasn't found. Bomb out and
                # start the next word.
                if next_offset == -1:
                    break

                selected.append(next_offset)
                start_offset = next_offset + len(word)

        return word_positions

    def find_window(self, highlight_locations, max_window):
        """ Find the window to highlight. Uses the value of max_window
        to find the window with the most hits to be highlighted.

        If there are no places to highlight, returns the start and end of the text_block.
        """
        best_start = 0
        best_end = max_window

        # First, make sure we have words, or that we're even trying to limit
        # the window to highlight words
        if not highlight_locations or not self.max_window:
            return (best_start, best_end)

        word_offsets = []

        # Next, make sure we found any words at all.
        for word, offset_list in highlight_locations.items():
            if offset_list:
                # Add all of the locations to the list.
                word_offsets.extend(offset_list)

        if not word_offsets:
            return (best_start, best_end)

        # Only one word was found. It's first letter marks the window start, and the end
        # defined will be max_window characters after
        if len(word_offsets) == 1:
            return (word_offsets[0], word_offsets[0] + max_window)

        # Sort the list so it's in ascending order.
        word_offsets = sorted(word_offsets)
        best_start = word_offsets[0]
        best_end = best_start + max_window

        # We now have a denormalized list of all positions where a word was
        # found. We'll iterate through and find the densest window we can by
        # counting the number of found offsets (-1 to fit in the window).
        highest_density = 0
        for count, start in enumerate(word_offsets):
            current_density = 1

            for end in word_offsets[count + 1:]:
                if end - start < max_window:
                    current_density += 1
                else:
                    current_density = 0

                # Only replace if we have a bigger (not equal density) so we
                # give deference to windows earlier in the document.
                if current_density > highest_density:
                    best_start = start
                    best_end = start + max_window
                    highest_density = current_density

        return (best_start, best_end)

    def render_html(self, text_block, highlight_locations=None, start_offset=None, end_offset=None):
        # Start by chopping the block down to the proper window.
        text = text_block[start_offset:end_offset]

        # Invert highlight_locations to a location -> term list
        term_list = []

        for term, locations in highlight_locations.items():
            term_list += [(loc - start_offset, term) for loc in locations]

        loc_to_term = sorted(term_list)

        # Prepare the highlight template
        if self.css_class:
            hl_start = format_html('<{} class="{}">', self.html_tag, self.css_class)
        else:
            hl_start = format_html('<{}>', self.html_tag)

        hl_end = format_html('</{}>', self.html_tag)

        # Copy the part from the start of the string to the first match,
        # and there replace the match with a highlighted version.
        highlighted_chunk = ""
        matched_so_far = 0
        prev = 0
        prev_str = ""

        for cur, cur_str in loc_to_term:
            # This can be in a different case than cur_str
            actual_term = text[cur:cur + len(cur_str)]

            # Handle incorrect highlight_locations by first checking for the term
            if actual_term.lower() == cur_str:
                if cur < prev + len(prev_str):
                    continue

                highlighted_chunk += text[prev + len(prev_str):cur] + hl_start + actual_term + hl_end
                prev = cur
                prev_str = cur_str

                # Keep track of how far we've copied so far, for the last step
                matched_so_far = cur + len(actual_term)

        # Don't forget the chunk after the last term
        highlighted_chunk += text[matched_so_far:]

        if start_offset > 0:
            if self.trim:
                highlighted_chunk = u'\N{HORIZONTAL ELLIPSIS}%s' % highlighted_chunk
            else:
                highlighted_chunk = '%s%s' % (text_block[0:start_offset], highlighted_chunk)

        if end_offset < len(text_block):
            if self.trim:
                highlighted_chunk = u'%s\N{HORIZONTAL ELLIPSIS}' % highlighted_chunk
            else:
                highlighted_chunk = '%s%s' % (highlighted_chunk, text_block[end_offset:])

        return mark_safe(highlighted_chunk)
