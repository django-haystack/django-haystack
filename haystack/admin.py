from django import VERSION as django_version
from django.contrib.admin.options import ModelAdmin, csrf_protect_m
from django.contrib.admin.views.main import SEARCH_VAR, ChangeList
from django.core.exceptions import PermissionDenied
from django.core.paginator import InvalidPage, Paginator
from django.shortcuts import render
from django.utils.encoding import force_str
from django.utils.translation import ngettext

from haystack import connections
from haystack.constants import DEFAULT_ALIAS
from haystack.query import SearchQuerySet
from haystack.utils import get_model_ct_tuple


class SearchChangeList(ChangeList):
    def __init__(self, **kwargs):
        self.haystack_connection = kwargs.pop("haystack_connection", DEFAULT_ALIAS)
        super_kwargs = kwargs
        if django_version[0] >= 4:
            super_kwargs["search_help_text"] = "Search..."
        super().__init__(**super_kwargs)

    def get_results(self, request):
        if SEARCH_VAR not in request.GET:
            return super().get_results(request)

        # Note that pagination is 0-based, not 1-based.
        sqs = (
            SearchQuerySet(self.haystack_connection)
            .models(self.model)
            .auto_query(request.GET[SEARCH_VAR])
            .load_all()
        )

        paginator = Paginator(sqs, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count
        full_result_count = (
            SearchQuerySet(self.haystack_connection).models(self.model).all().count()
        )

        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        try:
            result_list = paginator.page(self.page_num).object_list
            # Grab just the Django models, since that's what everything else is
            # expecting.
            result_list = [result.object for result in result_list]
        except InvalidPage:
            result_list = ()

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator


class SearchModelAdminMixin:
    # haystack connection to use for searching
    haystack_connection = DEFAULT_ALIAS

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        if SEARCH_VAR not in request.GET:
            # Do the usual song and dance.
            return super().changelist_view(request, extra_context)

        # Do a search of just this model and populate a Changelist with the
        # returned bits.
        indexed_models = (
            connections[self.haystack_connection]
            .get_unified_index()
            .get_indexed_models()
        )

        if self.model not in indexed_models:
            # Oops. That model isn't being indexed. Return the usual
            # behavior instead.
            return super().changelist_view(request, extra_context)

        # So. Much. Boilerplate.
        # Why copy-paste a few lines when you can copy-paste TONS of lines?
        list_display = list(self.list_display)

        kwargs = {
            "haystack_connection": self.haystack_connection,
            "request": request,
            "model": self.model,
            "list_display": list_display,
            "list_display_links": self.list_display_links,
            "list_filter": self.list_filter,
            "date_hierarchy": self.date_hierarchy,
            "search_fields": self.search_fields,
            "list_select_related": self.list_select_related,
            "list_per_page": self.list_per_page,
            "list_editable": self.list_editable,
            "list_max_show_all": self.list_max_show_all,
            "model_admin": self,
        }
        if hasattr(self, "get_sortable_by"):  # Django 2.1+
            kwargs["sortable_by"] = self.get_sortable_by(request)
        changelist = SearchChangeList(**kwargs)
        changelist.formset = None
        media = self.media

        # Build the action form and populate it with available actions.
        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields["action"].choices = self.get_action_choices(request)
        else:
            action_form = None

        selection_note = ngettext(
            "0 of %(count)d selected",
            "of %(count)d selected",
            len(changelist.result_list),
        )
        selection_note_all = ngettext(
            "%(total_count)s selected",
            "All %(total_count)s selected",
            changelist.result_count,
        )

        context = {
            "module_name": force_str(self.model._meta.verbose_name_plural),
            "selection_note": selection_note % {"count": len(changelist.result_list)},
            "selection_note_all": selection_note_all
            % {"total_count": changelist.result_count},
            "title": changelist.title,
            "is_popup": changelist.is_popup,
            "cl": changelist,
            "media": media,
            "has_add_permission": self.has_add_permission(request),
            "opts": changelist.opts,
            "app_label": self.model._meta.app_label,
            "action_form": action_form,
            "actions_on_top": self.actions_on_top,
            "actions_on_bottom": self.actions_on_bottom,
            "actions_selection_counter": getattr(self, "actions_selection_counter", 0),
        }
        context.update(extra_context or {})
        request.current_app = self.admin_site.name
        app_name, model_name = get_model_ct_tuple(self.model)
        return render(
            request,
            self.change_list_template
            or [
                "admin/%s/%s/change_list.html" % (app_name, model_name),
                "admin/%s/change_list.html" % app_name,
                "admin/change_list.html",
            ],
            context,
        )


class SearchModelAdmin(SearchModelAdminMixin, ModelAdmin):
    pass
