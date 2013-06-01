from __future__ import unicode_literals
from haystack.query import SearchQuerySet, EmptySearchQuerySet


class SearchIndexManager(object):
    def __init__(self, using=None):
        super(SearchIndexManager, self).__init__()
        self.using = using

    def get_search_queryset(self):
        """Returns a new SearchQuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        return SearchQuerySet(using=self.using)

    def get_empty_query_set(self):
        return EmptySearchQuerySet(using=self.using)

    def all(self):
        return self.get_search_queryset()

    def none(self):
        return self.get_empty_query_set()

    def filter(self, *args, **kwargs):
        return self.get_search_queryset().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        return self.get_search_queryset().exclude(*args, **kwargs)

    def filter_and(self, *args, **kwargs):
        return self.get_search_queryset().filter_and(*args, **kwargs)

    def filter_or(self, *args, **kwargs):
        return self.get_search_queryset().filter_or(*args, **kwargs)

    def order_by(self, *args):
        return self.get_search_queryset().order_by(*args)

    def order_by_distance(self, **kwargs):
        return self.get_search_queryset().order_by_distance(**kwargs)

    def highlight(self):
        return self.get_search_queryset().highlight()

    def boost(self, term, boost):
        return self.get_search_queryset().boost(term, boost)

    def facet(self, field):
        return self.get_search_queryset().facet(field)

    def within(self, field, point_1, point_2):
        return self.get_search_queryset().within(field, point_1, point_2)

    def dwithin(self, field, point, distance):
        return self.get_search_queryset().dwithin(field, point, distance)

    def distance(self, field, point):
        return self.get_search_queryset().distance(field, point)

    def date_facet(self, field, start_date, end_date, gap_by, gap_amount=1):
        return self.get_search_queryset().date_facet(field, start_date, end_date, gap_by, gap_amount=1)

    def query_facet(self, field, query):
        return self.get_search_queryset().query_facet(field, query)

    def narrow(self, query):
        return self.get_search_queryset().narrow(query)

    def raw_search(self, query_string, **kwargs):
        return self.get_search_queryset().raw_search(query_string,  **kwargs)

    def load_all(self):
        return self.get_search_queryset().load_all()

    def auto_query(self, query_string, fieldname='content'):
        return self.get_search_queryset().auto_query(query_string, fieldname=fieldname)

    def autocomplete(self, **kwargs):
        return self.get_search_queryset().autocomplete(**kwargs)

    def using(self, connection_name):
        return self.get_search_queryset().using(connection_name)

    def count(self):
        return self.get_search_queryset().count()

    def best_match(self):
        return self.get_search_queryset().best_match()

    def latest(self, date_field):
        return self.get_search_queryset().latest(date_field)

    def more_like_this(self, model_instance):
        return self.get_search_queryset().more_like_this(model_instance)

    def facet_counts(self):
        return self.get_search_queryset().facet_counts()

    def spelling_suggestion(self, preferred_query=None):
        return self.get_search_queryset().spelling_suggestion(preferred_query=None)

    def values(self, *fields):
        return self.get_search_queryset().values(*fields)

    def values_list(self, *fields, **kwargs):
        return self.get_search_queryset().values_list(*fields, **kwargs)
