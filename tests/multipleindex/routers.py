from haystack import routers
from multipleindex.models import Baz
from multipleindex.search_indexes import BazIndex

class BazRouter(routers.BaseRouter):
    def for_read(self, models=None, **hints):
        if models is None:
            return None
        import pdb; pdb.set_trace()
        if Baz in models:
            return 'filtered_whoosh'
        return None

    def for_write(self, index=None, instance=None, **hints):
        if isinstance(instance, Baz):
            return 'filtered_whoosh'
        return None
