from django.template import loader, Context
from haystack.exceptions import SearchFieldError


# All the SearchFields variants.

class SearchField(object):
    """The base implementation of a search field."""
    def __init__(self, model_attr=None, use_template=False, template_name=None, 
                 document=False, indexed=True, stored=True, default=None,
                 null=False):
        # Track what the index thinks this field is called.
        self.instance_name = None
        self.model_attr = model_attr
        self.use_template = use_template
        self.template_name = template_name
        self.document = document
        self.indexed = indexed
        self.stored = stored
        self._default = default
        self.null = null
    
    @property
    def default(self):
        if callable(self._default):
            return self._default()
        
        return self._default
    
    def prepare(self, obj):
        # Give priority to a template.
        if self.use_template:
            return self.prepare_template(obj)
        elif self.model_attr is not None:
            # Check for `__` in the field for looking through the relation.
            attrs = self.model_attr.split('__')
            current_object = obj
            
            for attr in attrs:
                if not hasattr(current_object, attr):
                    return self._default
                
                current_object = getattr(current_object, attr)
            
            if callable(current_object):
                return current_object()
            
            return current_object
        
        return self.default
    
    def prepare_template(self, obj):
        """
        Flatten an object for indexing.
        
        This loads a template, ``search/indexes/{app_label}/{model_name}_{field_name}.txt``,
        and returns the result of rendering that template. ``object``
        will be in its context.
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError("This field requires either its instance_name variable to be populated or an explicit template_name in order to load the correct template.")
        
        if self.template_name is not None:
            template_name = self.template_name
        else:
            template_name = 'search/indexes/%s/%s_%s.txt' % (obj._meta.app_label, obj._meta.module_name, self.instance_name)
        
        t = loader.get_template(template_name)
        return t.render(Context({'object': obj}))


class CharField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = ''
        
        super(CharField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        return self.convert(super(CharField, self).prepare(obj))
    
    def convert(self, value):
        return unicode(value)


class IntegerField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = 0
        
        super(IntegerField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        prepared = super(IntegerField, self).prepare(obj)
        
        if prepared is None:
            return None
        
        return self.convert(prepared)
    
    def convert(self, value):
        return int(value)


class FloatField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = 0.0
        
        super(FloatField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        prepared = super(FloatField, self).prepare(obj)
        
        if prepared is None:
            return None
        
        return self.convert(prepared)
    
    def convert(self, value):
        return float(value)


class BooleanField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = False
        
        super(BooleanField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        return self.convert(super(BooleanField, self).prepare(obj))
    
    def convert(self, value):
        return bool(value)


class DateField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = ''
        
        super(DateField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        return super(DateField, self).prepare(obj)


class DateTimeField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = ''
        
        super(DateTimeField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        return super(DateTimeField, self).prepare(obj)


class MultiValueField(SearchField):
    def __init__(self, **kwargs):
        if not 'default' in kwargs:
            kwargs['default'] = ''
        
        super(MultiValueField, self).__init__(**kwargs)
    
    def prepare(self, obj):
        return self.convert(super(MultiValueField, self).prepare(obj))
    
    def convert(self, value):
        return list(value)
