"""Tests for Whoosh spelling suggestions"""

from django.conf import settings
from django.http import HttpRequest

from haystack.forms import SearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView

from .test_whoosh_backend import LiveWhooshRoundTripTestCase


class SpellingSuggestionTestCase(LiveWhooshRoundTripTestCase):
    fixtures = ["base_data"]

    def setUp(self):
        self.old_spelling_setting = settings.HAYSTACK_CONNECTIONS["whoosh"].get(
            "INCLUDE_SPELLING", False
        )
        settings.HAYSTACK_CONNECTIONS["whoosh"]["INCLUDE_SPELLING"] = True

        super().setUp()

    def tearDown(self):
        settings.HAYSTACK_CONNECTIONS["whoosh"][
            "INCLUDE_SPELLING"
        ] = self.old_spelling_setting
        super().tearDown()

    def test_form_suggestion(self):
        form = SearchForm({"q": "exampl"}, searchqueryset=SearchQuerySet("whoosh"))
        self.assertEqual(form.get_suggestion(), "example")

    def test_view_suggestion(self):
        view = SearchView(
            template="test_suggestion.html", searchqueryset=SearchQuerySet("whoosh")
        )
        mock = HttpRequest()
        mock.GET["q"] = "exampl"
        resp = view(mock)
        self.assertEqual(resp.content, b"Suggestion: example\n")
