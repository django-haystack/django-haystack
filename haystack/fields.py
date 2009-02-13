from django.template import loader, Context


class SearchFieldError(Exception):
    pass


# All the SearchFields variants.

class SearchField(object):
    """The base implementation of a search field."""
    def __init__(self, document=False, indexed=True, stored=True):
        # Track what the index thinks this field is called.
        self.instance_name = None
        self.document = document
        self.indexed = indexed
        self.stored = stored
    
    def get_value(self, obj):
        raise NotImplementedError('Please use a subclass of SearchField.')


class ModelField(SearchField):
    def __init__(self, model_field=None, **kwargs):
        if model_field is None:
            raise SearchFieldError('You must specify the field of the model to attach the search field to.')
        
        self.model_field = model_field
        super(ModelField, self).__init__(**kwargs)


class CharField(ModelField):
    def get_value(self, obj):
        return unicode(getattr(obj, self.model_field, ''))


class IntegerField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, 0)


class FloatField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, 0.0)


class BooleanField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, False)


class DateField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, '')


class DateTimeField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, '')


class MultiValueField(ModelField):
    def get_value(self, obj):
        return getattr(obj, self.model_field, [])


class TemplateField(SearchField):
    def __init__(self, template_name=None, **kwargs):
        self.template_name = template_name
        super(TemplateField, self).__init__(**kwargs)
    
    def get_value(self, obj):
        """
        Flatten an object for indexing.
        
        This loads a template, ``search/indexes/{app_label}/{model_name}.txt``,
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
