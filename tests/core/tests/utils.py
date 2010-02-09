from django.test import TestCase
from haystack.utils import get_identifier, Highlighter
from core.models import MockModel


class GetIdentifierTestCase(TestCase):
    def test_get_identifier(self):
        # Various invalid identifiers.
        self.assertRaises(AttributeError, get_identifier, 'core')
        self.assertRaises(AttributeError, get_identifier, 'core.mockmodel')
        self.assertRaises(AttributeError, get_identifier, 'core.mockmodel.foo')
        self.assertRaises(AttributeError, get_identifier, 'core-app.mockmodel.1')
        
        # Valid string identifier.
        self.assertEqual(get_identifier('core.mockmodel.1'), 'core.mockmodel.1')
        
        # Valid object.
        mock = MockModel.objects.get(pk=1)
        self.assertEqual(get_identifier(mock), 'core.mockmodel.1')


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
