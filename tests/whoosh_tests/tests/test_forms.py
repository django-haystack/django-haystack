# To ensure spelling suggestions work...
from django.conf import settings
from django.http import HttpRequest
from haystack.forms import SearchForm
from haystack.views import SearchView
from whoosh_tests.tests.test_whoosh_backend import LiveWhooshRoundTripTestCase


class SpellingSuggestionTestCase(LiveWhooshRoundTripTestCase):
    def setUp(self):
        self.old_spelling_setting = settings.HAYSTACK_CONNECTIONS['default']['INCLUDE_SPELLING']
        settings.HAYSTACK_CONNECTIONS['default']['INCLUDE_SPELLING'] = True

        super(SpellingSuggestionTestCase, self).setUp()

    def tearDown(self):
        settings.HAYSTACK_CONNECTIONS['default']['INCLUDE_SPELLING'] = self.old_spelling_setting
        super(SpellingSuggestionTestCase, self).tearDown()

    def test_form_suggestion(self):
        form = SearchForm({'q': 'exampl'})
        self.assertEqual(form.get_suggestion(), 'example')

    def test_view_suggestion(self):
        view = SearchView(template='test_suggestion.html')
        mock = HttpRequest()
        mock.GET['q'] = 'exampl'
        resp = view(mock)
        self.assertEqual(resp.content, b'Suggestion: example')
