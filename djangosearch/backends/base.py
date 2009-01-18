from djangosearch.query import RELEVANCE
from django.utils.encoding import force_unicode

class SearchEngine(object):
    """
    Abstract search engine base class.
    """

    def get_identifier(self, obj):
        """
        Get an unique identifier for the object.

        If not overridden, uses <app_label>.<object_name>.<pk>.
        """
        return "%s.%s.%s" % (obj._meta.app_label, obj._meta.module_name, obj._get_pk_val())

    def update(self, indexer, iterable):
        raise NotImplementedError

    def remove(self, obj):
        raise NotImplementedError

    def clear(self, models):
        raise NotImplementedError

    def search(self, query, models=None, order_by=RELEVANCE, limit=None, offset=None):
        raise NotImplementedError

    def prep_value(self, db_field, value):
        """
        Hook to give the backend a chance to prep an attribute value before
        sending it to the search engine. By default, just force it to unicode.
        """
        return force_unicode(value)
