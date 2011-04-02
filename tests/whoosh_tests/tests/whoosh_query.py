import datetime
import os
from django.conf import settings
from django.test import TestCase
from haystack.backends.whoosh_backend import SearchBackend, SearchQuery
from haystack.models import SearchResult
from haystack.query import SQ
from core.models import MockModel, AnotherMockModel


class WhooshSearchQueryTestCase(TestCase):
    def setUp(self):
        super(WhooshSearchQueryTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.sq = SearchQuery(backend=SearchBackend())
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            index_files = os.listdir(settings.HAYSTACK_WHOOSH_PATH)
        
            for index_file in index_files:
                os.remove(os.path.join(settings.HAYSTACK_WHOOSH_PATH, index_file))
        
            os.removedirs(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        super(WhooshSearchQueryTestCase, self).tearDown()
    
    def test_build_query_all(self):
        self.assertEqual(self.sq.build_query(), '*')
    
    def test_build_query_single_word(self):
        self.sq.add_filter(SQ(content='hello'))
        self.assertEqual(self.sq.build_query(), 'hello')
    
    def test_build_query_multiple_words_and(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_filter(SQ(content='world'))
        self.assertEqual(self.sq.build_query(), u'(hello AND world)')
    
    def test_build_query_multiple_words_not(self):
        self.sq.add_filter(~SQ(content='hello'))
        self.sq.add_filter(~SQ(content='world'))
        self.assertEqual(self.sq.build_query(), u'(NOT (hello) AND NOT (world))')
    
    def test_build_query_multiple_words_or(self):
        self.sq.add_filter(SQ(content='hello') | SQ(content='world'))
        self.assertEqual(self.sq.build_query(), u'(hello OR world)')
    
    def test_build_query_multiple_words_mixed(self):
        self.sq.add_filter(SQ(content='why') | SQ(content='hello'))
        self.sq.add_filter(~SQ(content='world'))
        self.assertEqual(self.sq.build_query(), u'((why OR hello) AND NOT (world))')
    
    def test_build_query_phrase(self):
        self.sq.add_filter(SQ(content='hello world'))
        self.assertEqual(self.sq.build_query(), '"hello world"')
    
    def test_build_query_boost(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_boost('world', 5)
        self.assertEqual(self.sq.build_query(), "hello world^5")
    
    def test_build_query_multiple_filter_types(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(pub_date__lte=datetime.datetime(2009, 2, 10, 1, 59)))
        self.sq.add_filter(SQ(author__gt='daniel'))
        self.sq.add_filter(SQ(created__lt=datetime.datetime(2009, 2, 12, 12, 13)))
        self.sq.add_filter(SQ(title__gte='B'))
        self.sq.add_filter(SQ(id__in=[1, 2, 3]))
        self.sq.add_filter(SQ(rating__range=[3, 5]))
        self.assertEqual(self.sq.build_query(), u'(why AND pub_date:[to 20090210015900] AND author:{daniel to} AND created:{to 20090212121300} AND title:[B to] AND (id:"1" OR id:"2" OR id:"3") AND rating:[3 to 5])')
    
    def test_build_query_in_filter_multiple_words(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(title__in=["A Famous Paper", "An Infamous Article"]))
        self.assertEqual(self.sq.build_query(), u'(why AND (title:"A Famous Paper" OR title:"An Infamous Article"))')
    
    def test_build_query_in_filter_datetime(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(pub_date__in=[datetime.datetime(2009, 7, 6, 1, 56, 21)]))
        self.assertEqual(self.sq.build_query(), u'(why AND (pub_date:"20090706015621"))')
    
    def test_build_query_wildcard_filter_types(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(title__startswith='haystack'))
        self.assertEqual(self.sq.build_query(), u'(why AND title:haystack*)')
    
    def test_clean(self):
        self.assertEqual(self.sq.clean('hello world'), 'hello world')
        self.assertEqual(self.sq.clean('hello AND world'), 'hello and world')
        self.assertEqual(self.sq.clean('hello AND OR NOT TO + - && || ! ( ) { } [ ] ^ " ~ * ? : \ world'), 'hello and or not to \'+\' \'-\' \'&&\' \'||\' \'!\' \'(\' \')\' \'{\' \'}\' \'[\' \']\' \'^\' \'"\' \'~\' \'*\' \'?\' \':\' \'\\\' world')
        self.assertEqual(self.sq.clean('so please NOTe i am in a bAND and bORed'), 'so please NOTe i am in a bAND and bORed')
    
    def test_build_query_with_models(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_model(MockModel)
        self.assertEqual(self.sq.build_query(), '(hello) AND (django_ct:core.mockmodel)')
        
        self.sq.add_model(AnotherMockModel)
        self.assertEqual(self.sq.build_query(), u'(hello) AND (django_ct:core.anothermockmodel OR django_ct:core.mockmodel)')
    
    def test_build_query_with_datetime(self):
        self.sq.add_filter(SQ(pub_date=datetime.datetime(2009, 5, 9, 16, 20)))
        self.assertEqual(self.sq.build_query(), u'pub_date:20090509162000')
    
    def test_build_query_with_sequence_and_filter_not_in(self):
        self.sq.add_filter(SQ(id__exact=[1, 2, 3]))
        self.assertEqual(self.sq.build_query(), u'id:1,2,3')
    
    def test_set_result_class(self):
        # Assert that we're defaulting to ``SearchResult``.
        self.assertTrue(issubclass(self.sq.result_class, SearchResult))
        
        # Custom class.
        class IttyBittyResult(object):
            pass
        
        self.sq.set_result_class(IttyBittyResult)
        self.assertTrue(issubclass(self.sq.result_class, IttyBittyResult))
        
        # Reset to default.
        self.sq.set_result_class(None)
        self.assertTrue(issubclass(self.sq.result_class, SearchResult))
