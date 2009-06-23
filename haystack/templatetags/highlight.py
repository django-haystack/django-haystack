from django.conf import settings
from django import template
from haystack.utils import highlighter


register = template.Library()


class HighlightNode(template.Node):
    def __init__(self, text_block, query, css_class='highlighted', max_words=200):
        self.text_block = template.Variable(text_block)
        self.query = template.Variable(query)
        self.css_class = css_class
        self.max_words = max_words
    
    def render(self, context):
        text_block = self.model.resolve(text_block)
        query = self.model.resolve(query)
        highlighted_text = ''
        
        # Handle a user-defined highlighting function.
        if hasattr(settings, 'HAYSTACK_CUSTOM_HIGHLIGHTER'):
            # Do the import dance.
        else:
            highlighted_text = highlighter(text_block, query, css_class, max_words)
        
        return ''


@register.tag
def highlight(parser, token):
    """
    Takes a block of text and highlights words from a provided query within that
    block of text. Optionally accepts an argument to provide the CSS class to
    wrap highlighted word in.
    
    Syntax::
    
        {% highlight <text_block> with <query> [class "class_name"] [max_words 200] %}
    
    Example::
    
        # Highlight summary with default behavior.
        {% highlight result.summary with request.query %}
        
        # Highlight summary but wrap highlighted words with a span and the
        # following CSS class.
        {% highlight result.summary with request.query class "highlight_me_please" %}
    """
    bits = token.split_contents()
    
    if not len(bits) in (4, 6):
        raise template.TemplateSyntaxError(u"'%s' tag requires either 3 or 5 arguments." % bits[0])
    
    text_block = bits[1]
    
    if bits[2] != 'with':
        raise template.TemplateSyntaxError(u"'%s' tag's second argument should be 'with'." % bits[0])
    
    query = bits[3]
    css_class = None
    max_words = 200
    
    if len(bits) == 6:
        if not bits[4] in ('class', 'max_words'):
            raise template.TemplateSyntaxError(u"'%s' tag's fourth argument should be either 'class' or 'max_words'." % bits[0])
        
        if bits[4] == 'class':
            css_class = bits[5]
        
        if bits[4] == 'max_words':
            max_words = bits[5]
    
    if len(bits) == 8:
        if bits[4] != 'class':
            raise template.TemplateSyntaxError(u"'%s' tag's fourth argument should be 'class'." % bits[0])
        
        css_class = bits[5]
        
        if bits[6] != 'max_words':
            raise template.TemplateSyntaxError(u"'%s' tag's sixth argument should be 'max_words'." % bits[0])
        
        max_words = bits[7]
    
    return HighlightNode(text_block, query, css_class, max_words)
