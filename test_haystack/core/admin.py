from django.contrib import admin

from haystack.admin import SearchModelAdmin

from .models import MockModel


@admin.register(MockModel)
class MockModelAdmin(SearchModelAdmin):
    haystack_connection = "solr"
    date_hierarchy = "pub_date"
    list_display = ("author", "pub_date")
