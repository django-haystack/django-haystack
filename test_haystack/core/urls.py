# encoding: utf-8
from django.conf.urls import include, url
from django.contrib import admin

from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import FacetedSearchView, SearchView, basic_search

admin.autodiscover()


urlpatterns = [
    url(r"^admin/", admin.site.urls),
    url(r"^$", SearchView(load_all=False), name="haystack_search"),
    url(
        r"^faceted/$",
        FacetedSearchView(
            searchqueryset=SearchQuerySet().facet("author"),
            form_class=FacetedSearchForm,
        ),
        name="haystack_faceted_search",
    ),
    url(r"^basic/$", basic_search, {"load_all": False}, name="haystack_basic_search"),
]

urlpatterns += [
    url(
        r"",
        include(("test_haystack.test_app_without_models.urls", "app-without-models")),
    )
]
