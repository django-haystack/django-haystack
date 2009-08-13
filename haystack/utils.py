class Highlighter(object):
    css_class = 'highlighted'
    html_tag = 'span'
    max_words = 200
    text_block = ''
    
    def __init__(self, query, max_words=None, html_tag=None, css_class=None):
        self.query = query
        
        if max_words is not None:
            self.max_words = int(max_words)
        
        if html_tag is not None:
            self.html_tag = html_tag
        
        if css_class is not None:
            self.css_class = css_class
    
    def highlight(self, text_block):
        self.text_block = text_block
        highlight_locations = self.find_highlightable_words()
        start_offset, end_offset = self.find_window(highlight_locations)
        return self.render_html(highlight_locations, start_offset, end_offset)
    
    def find_highlightable_words(self):
        pass
    
    def find_window(self, highlight_locations):
        pass
    
    def render_html(self, highlight_locations=None, start_offset=None, end_offset=None):
        highlighted_chunk = self.text_block
