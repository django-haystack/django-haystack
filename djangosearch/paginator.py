from django.core.paginator import InvalidPage, Paginator, Page


class SearchPaginator(Paginator):
    def __init__(self, results, per_page, orphans=0, allow_empty_first_page=True):
        self.results = results
        self.per_page = per_page
        self.orphans = orphans
        self.allow_empty_first_page = allow_empty_first_page
        self._num_pages = self._count = None

    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        number = self.validate_number(number)
        # DRL_FIXME: This should dispatch to the SearchQuery to pull the right
        #            range, rather than forcing the app developer to manually
        #            handle their own offsets.
        return Page(list(self.results), number, self)
