from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.views.main import ChangeList, SEARCH_VAR
from django.core.paginator import Paginator, InvalidPage
from haystack import connections
from haystack.query import SearchQuerySet

def list_max_show_all(changelist):
    """
    Returns the maximum amount of results a changelist can have for the
    "Show all" link to be displayed in a manner compatible with both Django
    1.4 and 1.3. See Django ticket #15997 for details.
    """
    try:
        # This import is available in Django 1.3 and below
        from django.contrib.admin.views.main import MAX_SHOW_ALL_ALLOWED
        return MAX_SHOW_ALL_ALLOWED
    except ImportError:
        return changelist.list_max_show_all


class SearchChangeList(ChangeList):
    def get_results(self, request):
        if not SEARCH_VAR in request.GET or request.GET[SEARCH_VAR] == "":
            return super(SearchChangeList, self).get_results(request)

        # Note that pagination is 0-based, not 1-based.
        sqs = SearchQuerySet().models(self.model).auto_query(request.GET[SEARCH_VAR]).load_all()

        paginator = Paginator(sqs, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count
        full_result_count = SearchQuerySet().models(self.model).all().count()

        can_show_all = result_count <= list_max_show_all(self)
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        try:
            result_list = paginator.page(self.page_num+1).object_list
            # Grab just the Django models, since that's what everything else is
            # expecting.
            resolved_result_list = []
            for result in result_list:
                if result != None:
                    resolved_result_list.append(result.object)
                else:
                    result_count = result_count - 1
                    full_result_count = full_result_count - 1
            result_list = resolved_result_list
        except InvalidPage:
            result_list = ()

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator


class SearchModelAdmin(ModelAdmin):
    def get_changelist(self, request, **kwargs):
        if self.model in connections['default'].get_unified_index().get_indexed_models():
            return SearchChangeList
        else:
            return super(SearchModelAdmin, self).get_changelist(request, **kwargs)