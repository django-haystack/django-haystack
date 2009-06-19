from django import template
from haystack.query import SearchQuerySet


register = template.Library()


class MoreLikeThisNode(template.Node):
    def __init__(self, model, varname, limit=None):
        self.model = template.Variable(model)
        self.varname = varname
        self.limit = int(limit)
    
    def render(self, context):
        model_instance = self.model.resolve(context)
        sqs = SearchQuerySet().more_like_this(model_instance)
        
        if self.limit:
            sqs = sqs[:self.limit]
        
        context[self.varname] = sqs
        return ''


@register.tag
def more_like_this(parser, token):
    """
    Fetches similar items from the search index to find content that is similar
    to the provided model's content.
    
    Syntax::
    
        {% more_like_this model_instance as varname [limit n] %}
    
    Example::
    
        # Pull a full SearchQuerySet (lazy loaded) of similar content.
        {% more_like_this entry as related_content %}
        
        # Pull just the top 5 similar pieces of content.
        {% more_like_this entry as related_content limit 5  %}
    """
    bits = token.split_contents()
    
    if not len(bits) in (4, 6):
        raise template.TemplateSyntaxError(u"'%s' tag requires either 3 or 5 arguments." % bits[0])
    
    model = bits[1]
    
    if bits[2] != 'as':
        raise template.TemplateSyntaxError(u"'%s' tag's second argument should be 'as'." % bits[0])
    
    varname = bits[3]
    limit = None
    
    if len(bits) == 6:
        if bits[4] != 'limit':
            raise template.TemplateSyntaxError(u"'%s' tag's fourth argument should be 'limit'." % bits[0])
        
        limit = bits[5]
    
    return MoreLikeThisNode(model, varname, limit)
