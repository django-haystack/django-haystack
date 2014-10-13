.. _ref-admin:

===================
Django Admin Search
===================

Haystack comes with a base class to support searching via Haystack in the
Django admin. To use Haystack to search, inherit from ``haystack.admin.SearchModelAdmin``
instead of ``django.contrib.admin.ModelAdmin``.

For example::

    from haystack.admin import SearchModelAdmin
    from .models import MockModel


    class MockModelAdmin(SearchModelAdmin):
        haystack_connection = 'solr'
        date_hierarchy = 'pub_date'
        list_display = ('author', 'pub_date')


    admin.site.register(MockModel, MockModelAdmin)

You can also specify the Haystack connection used by the search with the
``haystack_connection`` property on the model admin class. If not specified,
the default connection will be used.

If you already have a base model admin class you use, there is also a mixin
you can use instead::

    from django.contrib import admin
    from haystack.admin import SearchModelAdminMixin
    from .models import MockModel


    class MyCustomModelAdmin(admin.ModelAdmin):
        pass


    class MockModelAdmin(SearchModelAdminMixin, MyCustomModelAdmin):
        haystack_connection = 'solr'
        date_hierarchy = 'pub_date'
        list_display = ('author', 'pub_date')


    admin.site.register(MockModel, MockModelAdmin)
