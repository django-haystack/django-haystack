from haystack import routers
from multipleindex.models import Baz
from multipleindex.search_indexes import BazIndex

class BazRouter(routers.BaseRouter):
    def for_read(self, models=None, **hints):
        return None

    def for_write(self, index=None, instance=None, **hints):
        if isinstance(instance, Baz):
            return 'filtered_whoosh'
        return None
