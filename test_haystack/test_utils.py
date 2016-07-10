# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase
from django.test.utils import override_settings
from test_haystack.core.models import MockModel

from haystack.utils import _lookup_identifier_method, get_facet_field_name, get_identifier, Highlighter, log


class GetIdentifierTestCase(TestCase):
    def test_get_facet_field_name(self):
        self.assertEqual(get_facet_field_name('id'), 'id')
        self.assertEqual(get_facet_field_name('django_id'), 'django_id')
        self.assertEqual(get_facet_field_name('django_ct'), 'django_ct')
        self.assertEqual(get_facet_field_name('author'), 'author_exact')
        self.assertEqual(get_facet_field_name('author_exact'), 'author_exact_exact')


class GetFacetFieldNameTestCase(TestCase):
    fixtures = ['base_data']

    def test_get_identifier(self):
        self.assertEqual(get_identifier('core.mockmodel.1'), 'core.mockmodel.1')

        # Valid object.
        mock = MockModel.objects.get(pk=1)
        self.assertEqual(get_identifier(mock), 'core.mockmodel.1')

    @override_settings(HAYSTACK_IDENTIFIER_METHOD='test_haystack.core.custom_identifier.get_identifier_method')
    def test_haystack_identifier_method(self):
        get_identifier = _lookup_identifier_method()
        self.assertEqual(get_identifier('a.b.c'), 'a.b.c')

    @override_settings(HAYSTACK_IDENTIFIER_METHOD='test_haystack.core.custom_identifier.not_there')
    def test_haystack_identifier_method_bad_path(self):
        self.assertRaises(AttributeError, _lookup_identifier_method)

    @override_settings(HAYSTACK_IDENTIFIER_METHOD='core.not_there.not_there')
    def test_haystack_identifier_method_bad_module(self):
        self.assertRaises(ImportError, _lookup_identifier_method)


class HighlighterTestCase(TestCase):
    def setUp(self):
        super(HighlighterTestCase, self).setUp()
        self.document_1 = "This is a test of the highlightable words detection. This is only a test. Were this an actual emergency, your text would have exploded in mid-air."
        self.document_2 = "The content of words in no particular order causes nothing to occur."
        self.document_3 = "%s %s" % (self.document_1, self.document_2)

    def test_find_highlightable_words(self):
        highlighter = Highlighter('this test')
        highlighter.text_block = self.document_1
        self.assertEqual(highlighter.find_highlightable_words(), {'this': [0, 53, 79], 'test': [10, 68]})

        # We don't stem for now.
        highlighter = Highlighter('highlight tests')
        highlighter.text_block = self.document_1
        self.assertEqual(highlighter.find_highlightable_words(), {'highlight': [22], 'tests': []})

        # Ignore negated bits.
        highlighter = Highlighter('highlight -test')
        highlighter.text_block = self.document_1
        self.assertEqual(highlighter.find_highlightable_words(), {'highlight': [22]})

    def test_find_window(self):
        # The query doesn't matter for this method, so ignore it.
        highlighter = Highlighter('')
        highlighter.text_block = self.document_1

        # No query.
        self.assertEqual(highlighter.find_window({}), (0, 200))

        # Nothing found.
        self.assertEqual(highlighter.find_window({'highlight': [], 'tests': []}), (0, 200))

        # Simple cases.
        self.assertEqual(highlighter.find_window({'highlight': [0], 'tests': [100]}), (0, 200))
        self.assertEqual(highlighter.find_window({'highlight': [99], 'tests': [199]}), (99, 299))
        self.assertEqual(highlighter.find_window({'highlight': [0], 'tests': [201]}), (0, 200))
        self.assertEqual(highlighter.find_window({'highlight': [203], 'tests': [120]}), (120, 320))
        self.assertEqual(highlighter.find_window({'highlight': [], 'tests': [100]}), (100, 300))
        self.assertEqual(highlighter.find_window({'highlight': [0], 'tests': [80], 'moof': [120]}), (0, 200))

        # Simple cases, with an outlier far outside the window.
        self.assertEqual(highlighter.find_window({'highlight': [0], 'tests': [100, 450]}), (0, 200))
        self.assertEqual(highlighter.find_window({'highlight': [100], 'tests': [220, 450]}), (100, 300))
        self.assertEqual(highlighter.find_window({'highlight': [100], 'tests': [350, 450]}), (350, 550))
        self.assertEqual(highlighter.find_window({'highlight': [100], 'tests': [220], 'moof': [450]}), (100, 300))

        # Density checks.
        self.assertEqual(highlighter.find_window({'highlight': [0], 'tests': [100, 180, 450]}), (0, 200))
        self.assertEqual(highlighter.find_window({'highlight': [0, 40], 'tests': [100, 200, 220, 450]}), (40, 240))
        self.assertEqual(highlighter.find_window({'highlight': [0, 40], 'tests': [100, 200, 220], 'moof': [450]}), (40, 240))
        self.assertEqual(highlighter.find_window({'highlight': [0, 40], 'tests': [100, 200, 220], 'moof': [294, 299, 450]}), (100, 300))

    def test_render_html(self):
        highlighter = Highlighter('this test')
        highlighter.text_block = self.document_1
        self.assertEqual(highlighter.render_html({'this': [0, 53, 79], 'test': [10, 68]}, 0, 200), '<span class="highlighted">This</span> is a <span class="highlighted">test</span> of the highlightable words detection. <span class="highlighted">This</span> is only a <span class="highlighted">test</span>. Were <span class="highlighted">this</span> an actual emergency, your text would have exploded in mid-air.')

        highlighter.text_block = self.document_2
        self.assertEqual(highlighter.render_html({'this': [0, 53, 79], 'test': [10, 68]}, 0, 200), 'The content of words in no particular order causes nothing to occur.')

        highlighter.text_block = self.document_3
        self.assertEqual(highlighter.render_html({'this': [0, 53, 79], 'test': [10, 68]}, 0, 200), '<span class="highlighted">This</span> is a <span class="highlighted">test</span> of the highlightable words detection. <span class="highlighted">This</span> is only a <span class="highlighted">test</span>. Were <span class="highlighted">this</span> an actual emergency, your text would have exploded in mid-air. The content of words in no particular order causes no...')

        highlighter = Highlighter('content detection')
        highlighter.text_block = self.document_3
        self.assertEqual(highlighter.render_html({'content': [151], 'detection': [42]}, 42, 242), '...<span class="highlighted">detection</span>. This is only a test. Were this an actual emergency, your text would have exploded in mid-air. The <span class="highlighted">content</span> of words in no particular order causes nothing to occur.')

        self.assertEqual(highlighter.render_html({'content': [151], 'detection': [42]}, 42, 200), '...<span class="highlighted">detection</span>. This is only a test. Were this an actual emergency, your text would have exploded in mid-air. The <span class="highlighted">content</span> of words in no particular order causes no...')

        # One term found within another term.
        highlighter = Highlighter('this is')
        highlighter.text_block = self.document_1
        self.assertEqual(highlighter.render_html({'this': [0, 53, 79], 'is': [2, 5, 55, 58, 81]}, 0, 200), '<span class="highlighted">This</span> <span class="highlighted">is</span> a test of the highlightable words detection. <span class="highlighted">This</span> <span class="highlighted">is</span> only a test. Were <span class="highlighted">this</span> an actual emergency, your text would have exploded in mid-air.')

        # Regression for repetition in the regular expression.
        highlighter = Highlighter('i++')
        highlighter.text_block = 'Foo is i++ in most cases.'
        self.assertEqual(highlighter.render_html({'i++': [7]}, 0, 200), 'Foo is <span class="highlighted">i++</span> in most cases.')
        highlighter = Highlighter('i**')
        highlighter.text_block = 'Foo is i** in most cases.'
        self.assertEqual(highlighter.render_html({'i**': [7]}, 0, 200), 'Foo is <span class="highlighted">i**</span> in most cases.')
        highlighter = Highlighter('i..')
        highlighter.text_block = 'Foo is i.. in most cases.'
        self.assertEqual(highlighter.render_html({'i..': [7]}, 0, 200), 'Foo is <span class="highlighted">i..</span> in most cases.')
        highlighter = Highlighter('i??')
        highlighter.text_block = 'Foo is i?? in most cases.'
        self.assertEqual(highlighter.render_html({'i??': [7]}, 0, 200), 'Foo is <span class="highlighted">i??</span> in most cases.')

        # Regression for highlighting already highlighted HTML terms.
        highlighter = Highlighter('span')
        highlighter.text_block = 'A span in spam makes html in a can.'
        self.assertEqual(highlighter.render_html({'span': [2]}, 0, 200), 'A <span class="highlighted">span</span> in spam makes html in a can.')

        highlighter = Highlighter('highlight')
        highlighter.text_block = 'A span in spam makes highlighted html in a can.'
        self.assertEqual(highlighter.render_html({'highlight': [21]}, 0, 200), 'A span in spam makes <span class="highlighted">highlight</span>ed html in a can.')

    def test_highlight(self):
        highlighter = Highlighter('this test')
        self.assertEqual(highlighter.highlight(self.document_1), u'<span class="highlighted">This</span> is a <span class="highlighted">test</span> of the highlightable words detection. <span class="highlighted">This</span> is only a <span class="highlighted">test</span>. Were <span class="highlighted">this</span> an actual emergency, your text would have exploded in mid-air.')
        self.assertEqual(highlighter.highlight(self.document_2), u'The content of words in no particular order causes nothing to occur.')
        self.assertEqual(highlighter.highlight(self.document_3), u'<span class="highlighted">This</span> is a <span class="highlighted">test</span> of the highlightable words detection. <span class="highlighted">This</span> is only a <span class="highlighted">test</span>. Were <span class="highlighted">this</span> an actual emergency, your text would have exploded in mid-air. The content of words in no particular order causes no...')

        highlighter = Highlighter('this test', html_tag='div', css_class=None)
        self.assertEqual(highlighter.highlight(self.document_1), u'<div>This</div> is a <div>test</div> of the highlightable words detection. <div>This</div> is only a <div>test</div>. Were <div>this</div> an actual emergency, your text would have exploded in mid-air.')
        self.assertEqual(highlighter.highlight(self.document_2), u'The content of words in no particular order causes nothing to occur.')
        self.assertEqual(highlighter.highlight(self.document_3), u'<div>This</div> is a <div>test</div> of the highlightable words detection. <div>This</div> is only a <div>test</div>. Were <div>this</div> an actual emergency, your text would have exploded in mid-air. The content of words in no particular order causes no...')

        highlighter = Highlighter('content detection')
        self.assertEqual(highlighter.highlight(self.document_1), u'...<span class="highlighted">detection</span>. This is only a test. Were this an actual emergency, your text would have exploded in mid-air.')
        self.assertEqual(highlighter.highlight(self.document_2), u'...<span class="highlighted">content</span> of words in no particular order causes nothing to occur.')
        self.assertEqual(highlighter.highlight(self.document_3), u'...<span class="highlighted">detection</span>. This is only a test. Were this an actual emergency, your text would have exploded in mid-air. The <span class="highlighted">content</span> of words in no particular order causes nothing to occur.')

        highlighter = Highlighter('content detection', max_length=100)
        self.assertEqual(highlighter.highlight(self.document_1), u'...<span class="highlighted">detection</span>. This is only a test. Were this an actual emergency, your text would have exploded in mid-...')
        self.assertEqual(highlighter.highlight(self.document_2), u'...<span class="highlighted">content</span> of words in no particular order causes nothing to occur.')
        self.assertEqual(highlighter.highlight(self.document_3), u'This is a test of the highlightable words <span class="highlighted">detection</span>. This is only a test. Were this an actual emerge...')


class LoggingFacadeTestCase(TestCase):
    def test_everything_noops_if_settings_are_off(self):
        with self.settings(HAYSTACK_LOGGING=False):
            l = log.LoggingFacade(None)
            l.error()

    def test_uses_provided_logger_if_logging_is_on(self):
        with self.settings(HAYSTACK_LOGGING=True):
            l = log.LoggingFacade(None)
            try:
                l.error()
            except AttributeError:
                pass

    def test_uses_provided_logger_by_default(self):
        class Logger(object):
            def __init__(self):
                self.was_called = False

            def error(self):
                self.was_called = True

        l = log.LoggingFacade(Logger())
        self.assertFalse(l.was_called, msg='sanity check')
        l.error()
        self.assertTrue(l.was_called)
