from django.contrib import admin
from haystack.admin import SearchModelAdmin
from core.models import MockModel


class MockModelAdmin(SearchModelAdmin):
    date_hierarchy = 'pub_date'
    list_display = ('author', 'pub_date')


admin.site.register(MockModel, MockModelAdmin)
