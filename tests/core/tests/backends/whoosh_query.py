import os
from django.conf import settings
from django.test import TestCase
from haystack.backends.whoosh_backend import SearchBackend, SearchQuery
from core.models import MockModel, AnotherMockModel


class WhooshSearchQueryTestCase(TestCase):
    def setUp(self):
        super(WhooshSearchQueryTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'WHOOSH_PATH', temp_path)
        settings.WHOOSH_PATH = temp_path
        
        self.sq = SearchQuery(backend=SearchBackend())
    
    def tearDown(self):
        if os.path.exists(settings.WHOOSH_PATH):
            index_files = os.listdir(settings.WHOOSH_PATH)
        
            for index_file in index_files:
                os.remove(os.path.join(settings.WHOOSH_PATH, index_file))
        
            os.removedirs(settings.WHOOSH_PATH)
        
        settings.WHOOSH_PATH = self.old_whoosh_path
        super(WhooshSearchQueryTestCase, self).tearDown()
    
    def test_build_query_all(self):
        self.assertEqual(self.sq.build_query(), '*')
    
    def test_build_query_single_word(self):
        self.sq.add_filter('content', 'hello')
        self.assertEqual(self.sq.build_query(), 'hello')
    
    def test_build_query_multiple_words_and(self):
        self.sq.add_filter('content', 'hello')
        self.sq.add_filter('content', 'world')
        self.assertEqual(self.sq.build_query(), 'hello AND world')
    
    def test_build_query_multiple_words_not(self):
        self.sq.add_filter('content', 'hello', use_not=True)
        self.sq.add_filter('content', 'world', use_not=True)
        self.assertEqual(self.sq.build_query(), 'NOT hello NOT world')
    
    def test_build_query_multiple_words_or(self):
        self.sq.add_filter('content', 'hello', use_or=True)
        self.sq.add_filter('content', 'world', use_or=True)
        self.assertEqual(self.sq.build_query(), 'hello OR world')
    
    def test_build_query_multiple_words_mixed(self):
        self.sq.add_filter('content', 'why')
        self.sq.add_filter('content', 'hello', use_or=True)
        self.sq.add_filter('content', 'world', use_not=True)
        self.assertEqual(self.sq.build_query(), 'why OR hello NOT world')
    
    def test_build_query_phrase(self):
        self.sq.add_filter('content', 'hello world')
        self.assertEqual(self.sq.build_query(), '"hello world"')
    
    def test_build_query_boost(self):
        self.sq.add_filter('content', 'hello')
        self.sq.add_boost('world', 5)
        self.assertEqual(self.sq.build_query(), "hello world^5")
    
    def test_build_query_multiple_filter_types(self):
        self.sq.add_filter('content', 'why')
        self.sq.add_filter('pub_date__lte', '2009-02-10 01:59:00')
        self.sq.add_filter('author__gt', 'daniel')
        self.sq.add_filter('created__lt', '2009-02-12 12:13:00')
        self.sq.add_filter('title__gte', 'B')
        self.sq.add_filter('id__in', [1, 2, 3])
        self.assertEqual(self.sq.build_query(), 'why AND NOT pub_date:"2009-02-10 01:59:00"..* AND author:daniel..* AND created:*.."2009-02-12 12:13:00" AND NOT title:*..B AND (id:1 OR id:2 OR id:3)')
    
    def test_clean(self):
        self.assertEqual(self.sq.clean('hello world'), 'hello world')
        self.assertEqual(self.sq.clean('hello AND world'), 'hello and world')
        self.assertEqual(self.sq.clean('hello AND OR NOT TO + - && || ! ( ) { } [ ] ^ " ~ * ? : \ world'), 'hello and or not to \\+ \\- \\&& \\|| \\! \\( \\) \\{ \\} \\[ \\] \\^ \\" \\~ \\* \\? \\: \\\\ world')
        self.assertEqual(self.sq.clean('so please NOTe i am in a bAND and bORed'), 'so please NOTe i am in a bAND and bORed')
    
    def test_build_query_with_models(self):
        self.sq.add_filter('content', 'hello')
        self.sq.add_model(MockModel)
        self.assertEqual(self.sq.build_query(), '(hello) AND (django_ct_s:"core.mockmodel")')
        
        self.sq.add_model(AnotherMockModel)
        self.assertEqual(self.sq.build_query(), '(hello) AND (django_ct_s:"core.mockmodel" OR django_ct_s:"core.anothermockmodel")')
