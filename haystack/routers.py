from haystack.constants import DEFAULT_ALIAS

from django.utils.translation import get_language

class BaseRouter(object):
    # Reserved for future extension.
    pass

class DefaultRouter(BaseRouter):
    def for_read(self, **hints):
        return DEFAULT_ALIAS
    
    def for_write(self, **hints):
        return DEFAULT_ALIAS
    
class LanguageRouter(BaseRouter):
    def for_read(self, **hints):
        return 'default_'+get_language()
    def for_write(self, **hints):
        return 'default_'+get_language()
