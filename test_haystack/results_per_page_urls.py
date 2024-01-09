from django.urls import path

from haystack.views import SearchView


class CustomPerPage(SearchView):
    results_per_page = 1


urlpatterns = [
    path("search/", CustomPerPage(load_all=False), name="haystack_search"),
    path(
        "search2/",
        CustomPerPage(load_all=False, results_per_page=2),
        name="haystack_search",
    ),
]
