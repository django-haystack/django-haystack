from django.contrib import admin
from django.urls import include, path

from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import FacetedSearchView, SearchView, basic_search

admin.autodiscover()


urlpatterns = [
    path("", SearchView(load_all=False), name="haystack_search"),
    path("admin/", admin.site.urls),
    path("basic/", basic_search, {"load_all": False}, name="haystack_basic_search"),
    path(
        "faceted/",
        FacetedSearchView(
            searchqueryset=SearchQuerySet().facet("author"),
            form_class=FacetedSearchForm,
        ),
        name="haystack_faceted_search",
    ),
]

urlpatterns += [
    path(
        "",
        include(("test_haystack.test_app_without_models.urls", "app-without-models")),
    )
]
