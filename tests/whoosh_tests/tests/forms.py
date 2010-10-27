# To ensure spelling suggestions work...
from django.conf import settings
from django.http import HttpRequest
from django.test import TestCase
from haystack.forms import SearchForm
from haystack.views import SearchView
from whoosh_tests.tests.whoosh_backend import LiveWhooshRoundTripTestCase


# Whoosh appears to flail on providing a useful suggestion, but since it's
# not ``None``, we know the backend is doing something. Whee.
class SpellingSuggestionTestCase(LiveWhooshRoundTripTestCase):
    def setUp(self):
        self.old_spelling_setting = getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False)
        settings.HAYSTACK_INCLUDE_SPELLING = True
        
        super(SpellingSuggestionTestCase, self).setUp()
    
    def tearDown(self):
        super(SpellingSuggestionTestCase, self).tearDown()
        settings.HAYSTACK_INCLUDE_SPELLING = self.old_spelling_setting
    
    def test_form_suggestion(self):
        form = SearchForm({'q': 'exampl'})
        self.assertEqual(form.get_suggestion(), '')
    
    def test_view_suggestion(self):
        view = SearchView(template='test_suggestion.html')
        mock = HttpRequest()
        mock.GET['q'] = 'exampl'
        resp = view(mock)
        self.assertEqual(resp.content, 'Suggestion: ')
