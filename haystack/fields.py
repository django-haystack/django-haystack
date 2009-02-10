from django.template import loader, Context


class SearchFieldError(Exception):
    pass


# All the SearchFields variants.

class SearchField(object):
    def __init__(self, db_field_name):
        # Track what the index thinks this field is called.
        self.instance_name = None
        # Track what part of the Model object we want.
        self.db_field_name = db_field_name
    
    def get_value(self, obj):
        return getattr(obj, self.db_field_name, '')


class CharField(SearchField):
    def get_value(self, obj):
        return unicode(getattr(obj, self.db_field_name, ''))


class NumberField(SearchField):
    pass


class DateField(SearchField):
    pass


class TimeField(SearchField):
    pass


class DateTimeField(SearchField):
    pass


class MultiValueField(SearchField):
    pass


class TemplateField(SearchField):
    def __init__(self, template_name=None):
        self.instance_name = None
        self.db_field_name = None
        self.template_name = template_name
    
    def get_value(self, obj):
        """
        Flatten an object for indexing.
        
        This loads a template, ``search/indexes/{app_label}/{model_name}.txt``,
        and returns the result of rendering that template. ``object``
        will be in its context.
        """
        if self.template_name is not None:
            template_name = self.template_name
        else:
            template_name = 'search/indexes/%s/%s.txt' % (obj._meta.app_label, obj._meta.module_name)
        
        t = loader.get_template(template_name)
        return t.render(Context({'object': obj}))


class ContentField(TemplateField):
    pass


class StoredField(TemplateField):
    def get_value(self, obj):
        """
        Flatten an object for storage (non-indexed).
        
        This is useful if you know in advance what you want to display in the
        search results and want to save on hits to the DB.
        
        This loads a template, by default 
        ``search/indexes/{app_label}/{model_name}_{instance_name}_stored.txt``,
        and returns the result of rendering that template. ``object``
        will be in its context. You can override this by passing the field a
        ``template_name`` parameter.
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError("This field requires its instance_name variable to be populated to load the correct template.")
        
        if self.template_name is not None:
            template_name = self.template_name
        else:
            template_name = 'search/indexes/%s/%s_%s_stored.txt' % (obj._meta.app_label, obj._meta.module_name, self.instance_name)
        
        t = loader.get_template(template_name)
        return t.render(Context({'object': obj}))
