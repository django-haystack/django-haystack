from django.template import loader, Context
from haystack.exceptions import SearchFieldError


class NOT_PROVIDED:
    pass


# All the SearchFields variants.

class SearchField(object):
    """The base implementation of a search field."""
    def __init__(self, model_attr=None, use_template=False, template_name=None,
                 document=False, indexed=True, stored=True, default=NOT_PROVIDED,
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
    
    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self._default is not NOT_PROVIDED
    
    @property
    def default(self):
        """Returns the default value for the field."""
        if callable(self._default):
            return self._default()
        
        return self._default
    
    def prepare(self, obj):
        """
        Takes data from the provided object and prepares it for storage in the
        index.
        """
        # Give priority to a template.
        if self.use_template:
            return self.prepare_template(obj)
        elif self.model_attr is not None:
            # Check for `__` in the field for looking through the relation.
            attrs = self.model_attr.split('__')
            current_object = obj
            
            for attr in attrs:
                if not hasattr(current_object, attr):
                    raise SearchFieldError("The model '%s' does not have a model_attr '%s'." % (repr(current_object), attr))
                
                current_object = getattr(current_object, attr, None)
                
                if current_object is None:
                    if self.has_default():
                        current_object = self._default
                        # Fall out of the loop, given any further attempts at
                        # accesses will fail misreably.
                        break
                    elif self.null:
                        current_object = None
                        # Fall out of the loop, given any further attempts at
                        # accesses will fail misreably.
                        break
                    else:
                        raise SearchFieldError("The model '%s' has an empty model_attr '%s' and doesn't allow a default or null value." % (repr(current_object), attr))
            
            if callable(current_object):
                return current_object()
            
            return current_object
        
        if self.has_default():
            return self.default
        else:
            return None
    
    def prepare_template(self, obj):
        """
        Flattens an object for indexing.
        
        This loads a template
        (``search/indexes/{app_label}/{model_name}_{field_name}.txt``) and
        returns the result of rendering that template. ``object`` will be in
        its context.
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError("This field requires either its instance_name variable to be populated or an explicit template_name in order to load the correct template.")
        
        if self.template_name is not None:
            template_name = self.template_name
        else:
            template_name = 'search/indexes/%s/%s_%s.txt' % (obj._meta.app_label, obj._meta.module_name, self.instance_name)
        
        t = loader.get_template(template_name)
        return t.render(Context({'object': obj}))
    
    def convert(self, value):
        """
        Handles conversion between the data found and the type of the field.
        
        Extending classes should override this method and provide correct
        data coercion.
        """
        return value


class CharField(SearchField):
    def prepare(self, obj):
        return self.convert(super(CharField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return unicode(value)


class IntegerField(SearchField):
    def prepare(self, obj):
        return self.convert(super(IntegerField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return int(value)


class FloatField(SearchField):
    def prepare(self, obj):
        return self.convert(super(FloatField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return float(value)


class BooleanField(SearchField):
    def prepare(self, obj):
        return self.convert(super(BooleanField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return bool(value)


class DateField(SearchField):
    def convert(self, value):
        if value is None:
            return None
        
        return str(value)


class DateTimeField(SearchField):
    def convert(self, value):
        if value is None:
            return None
        
        return str(value)


class MultiValueField(SearchField):
    def prepare(self, obj):
        return self.convert(super(MultiValueField, self).prepare(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return list(value)
