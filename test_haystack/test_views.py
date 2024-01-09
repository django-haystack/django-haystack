import queue
import time
from threading import Thread

from django import forms
from django.http import HttpRequest, QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse

from haystack import connections, indexes
from haystack.forms import FacetedSearchForm, ModelSearchForm, SearchForm
from haystack.query import EmptySearchQuerySet
from haystack.utils.loading import UnifiedIndex
from haystack.views import FacetedSearchView, SearchView, search_view_factory
from test_haystack.core.models import AnotherMockModel, MockModel


class InitialedSearchForm(SearchForm):
    q = forms.CharField(initial="Search for...", required=False, label="Search")


class BasicMockModelSearchIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def get_model(self):
        return MockModel


class BasicAnotherMockModelSearchIndex(indexes.BasicSearchIndex, indexes.Indexable):
    def get_model(self):
        return AnotherMockModel


class SearchViewTestCase(TestCase):
    fixtures = ["base_data"]

    def setUp(self):
        super().setUp()

        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super().tearDown()

    def test_search_no_query(self):
        response = self.client.get(reverse("haystack_search"))
        self.assertEqual(response.status_code, 200)

    def test_search_query(self):
        response = self.client.get(reverse("haystack_search"), {"q": "haystack"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("page", response.context)
        self.assertNotIn("page_obj", response.context)
        self.assertEqual(len(response.context[-1]["page"].object_list), 3)
        self.assertEqual(
            response.context[-1]["page"].object_list[0].content_type(), "core.mockmodel"
        )
        self.assertEqual(response.context[-1]["page"].object_list[0].pk, "1")

    def test_invalid_page(self):
        response = self.client.get(
            reverse("haystack_search"), {"q": "haystack", "page": "165233"}
        )
        self.assertEqual(response.status_code, 404)

    def test_empty_results(self):
        sv = SearchView()
        sv.request = HttpRequest()
        sv.form = sv.build_form()
        self.assertTrue(isinstance(sv.get_results(), EmptySearchQuerySet))

    def test_initial_data(self):
        sv = SearchView(form_class=InitialedSearchForm)
        sv.request = HttpRequest()
        form = sv.build_form()
        self.assertTrue(isinstance(form, InitialedSearchForm))
        self.assertEqual(form.fields["q"].initial, "Search for...")
        para = form.as_p()
        self.assertTrue('<label for="id_q">Search:</label>' in para)
        self.assertTrue('value="Search for..."' in para)

    def test_pagination(self):
        response = self.client.get(
            reverse("haystack_search"), {"q": "haystack", "page": 0}
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            reverse("haystack_search"), {"q": "haystack", "page": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]["page"].object_list), 3)
        response = self.client.get(
            reverse("haystack_search"), {"q": "haystack", "page": 2}
        )
        self.assertEqual(response.status_code, 404)

    def test_thread_safety(self):
        exceptions = []

        def threaded_view(resp_queue, view, request):
            time.sleep(2)

            try:
                view(request)
                resp_queue.put(request.GET["name"])
            except Exception as e:
                exceptions.append(e)
                raise

        class ThreadedSearchView(SearchView):
            def __call__(self, request):
                print("Name: %s" % request.GET["name"])
                return super().__call__(request)

        view = search_view_factory(view_class=ThreadedSearchView)
        resp_queue = queue.Queue()
        request_1 = HttpRequest()
        request_1.GET = {"name": "foo"}
        request_2 = HttpRequest()
        request_2.GET = {"name": "bar"}

        th1 = Thread(target=threaded_view, args=(resp_queue, view, request_1))
        th2 = Thread(target=threaded_view, args=(resp_queue, view, request_2))

        th1.start()
        th2.start()
        th1.join()
        th2.join()

        foo = resp_queue.get()
        bar = resp_queue.get()
        self.assertNotEqual(foo, bar)

    def test_spelling(self):
        # Stow.
        from django.conf import settings

        old = settings.HAYSTACK_CONNECTIONS["default"].get("INCLUDE_SPELLING", None)

        settings.HAYSTACK_CONNECTIONS["default"]["INCLUDE_SPELLING"] = True

        sv = SearchView()
        sv.query = "Nothing"
        sv.results = []
        sv.build_page = lambda: (None, None)
        sv.create_response()
        context = sv.get_context()

        self.assertIn(
            "suggestion",
            context,
            msg="Spelling suggestions should be present even if"
            " no results were returned",
        )
        self.assertEqual(context["suggestion"], None)

        # Restore
        settings.HAYSTACK_CONNECTIONS["default"]["INCLUDE_SPELLING"] = old

        if old is None:
            del settings.HAYSTACK_CONNECTIONS["default"]["INCLUDE_SPELLING"]


@override_settings(ROOT_URLCONF="test_haystack.results_per_page_urls")
class ResultsPerPageTestCase(TestCase):
    fixtures = ["base_data"]

    def setUp(self):
        super().setUp()

        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super().tearDown()

    def test_custom_results_per_page(self):
        response = self.client.get("/search/", {"q": "haystack"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]["page"].object_list), 1)
        self.assertEqual(response.context[-1]["paginator"].per_page, 1)

        response = self.client.get("/search2/", {"q": "hello world"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]["page"].object_list), 2)
        self.assertEqual(response.context[-1]["paginator"].per_page, 2)


class FacetedSearchViewTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super().tearDown()

    def test_search_no_query(self):
        response = self.client.get(reverse("haystack_faceted_search"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["facets"], {})

    def test_empty_results(self):
        fsv = FacetedSearchView()
        fsv.request = HttpRequest()
        fsv.request.GET = QueryDict("")
        fsv.form = fsv.build_form()
        self.assertTrue(isinstance(fsv.get_results(), EmptySearchQuerySet))

    def test_default_form(self):
        fsv = FacetedSearchView()
        fsv.request = HttpRequest()
        fsv.request.GET = QueryDict("")
        fsv.form = fsv.build_form()
        self.assertTrue(isinstance(fsv.form, FacetedSearchForm))

    def test_list_selected_facets(self):
        fsv = FacetedSearchView()
        fsv.request = HttpRequest()
        fsv.request.GET = QueryDict("")
        fsv.form = fsv.build_form()
        self.assertEqual(fsv.form.selected_facets, [])

        fsv = FacetedSearchView()
        fsv.request = HttpRequest()
        fsv.request.GET = QueryDict(
            "selected_facets=author:daniel&selected_facets=author:chris"
        )
        fsv.form = fsv.build_form()
        self.assertEqual(fsv.form.selected_facets, ["author:daniel", "author:chris"])


class BasicSearchViewTestCase(TestCase):
    fixtures = ["base_data"]

    def setUp(self):
        super().setUp()

        # Stow.
        self.old_unified_index = connections["default"]._index
        self.ui = UnifiedIndex()
        self.bmmsi = BasicMockModelSearchIndex()
        self.bammsi = BasicAnotherMockModelSearchIndex()
        self.ui.build(indexes=[self.bmmsi, self.bammsi])
        connections["default"]._index = self.ui

        # Update the "index".
        backend = connections["default"].get_backend()
        backend.clear()
        backend.update(self.bmmsi, MockModel.objects.all())

    def tearDown(self):
        connections["default"]._index = self.old_unified_index
        super().tearDown()

    def test_search_no_query(self):
        response = self.client.get(reverse("haystack_basic_search"))
        self.assertEqual(response.status_code, 200)

    def test_search_query(self):
        response = self.client.get(reverse("haystack_basic_search"), {"q": "haystack"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(type(response.context[-1]["form"]), ModelSearchForm)
        self.assertEqual(len(response.context[-1]["page"].object_list), 3)
        self.assertEqual(
            response.context[-1]["page"].object_list[0].content_type(), "core.mockmodel"
        )
        self.assertEqual(response.context[-1]["page"].object_list[0].pk, "1")
        self.assertEqual(response.context[-1]["query"], "haystack")

    def test_invalid_page(self):
        response = self.client.get(
            reverse("haystack_basic_search"), {"q": "haystack", "page": "165233"}
        )
        self.assertEqual(response.status_code, 404)
