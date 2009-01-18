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
        return Page(list(self.results), number, self)

    def _get_count(self):
        "Returns the total number of objects, across all pages."
        if self._count is None:
            self._count = self.results.hits
        return self._count
    count = property(_get_count)
