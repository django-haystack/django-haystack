from django.template import loader, Context


# All the SearchFields variants.

class SearchField(object):
    def __init__(self, db_field_name):
        self.db_field_name = db_field_name
    
    def get_value(self, obj):
        return getattr(obj, self.db_field_name, '')


class ContentField(SearchField):
    def __init__(self):
        self.db_field_name = None
    
    def get_value(self, obj):
        """
        Flatten an object for indexing.
        
        This loads a template, ``search/indexes/{app_label}/{model_name}.txt``
        and returns the result of rendering that template. ``object``
        will be in its context.
        """
        t = loader.get_template('search/indexes/%s/%s.txt' % (obj._meta.app_label, obj._meta.module_name))
        return t.render(Context({'object': obj}))


class CharField(SearchField):
    pass


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


class StoredField(SearchField):
    def __init__(self):
        self.db_field_name = None
    
    def get_value(self, obj):
        """
        Flatten an object for storage (non-indexed).
        
        This is useful if you know in advance what you want to display in the
        search results and want to save on hits to the DB.
        """
        t = loader.get_template('search/indexes/%s/%s_stored.txt' % (obj._meta.app_label, obj._meta.module_name))
        return t.render(Context({'object': obj}))
