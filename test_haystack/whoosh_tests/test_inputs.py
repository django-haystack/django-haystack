from django.test import TestCase

from haystack import connections, inputs


class WhooshInputTestCase(TestCase):
    def setUp(self):
        super(WhooshInputTestCase, self).setUp()
        self.query_obj = connections['whoosh'].get_query()

    def test_raw_init(self):
        raw = inputs.Raw('hello OR there, :you')
        self.assertEqual(raw.query_string, 'hello OR there, :you')
        self.assertEqual(raw.kwargs, {})
        self.assertEqual(raw.post_process, False)

        raw = inputs.Raw('hello OR there, :you', test='really')
        self.assertEqual(raw.query_string, 'hello OR there, :you')
        self.assertEqual(raw.kwargs, {'test': 'really'})
        self.assertEqual(raw.post_process, False)

    def test_raw_prepare(self):
        raw = inputs.Raw('hello OR there, :you')
        self.assertEqual(raw.prepare(self.query_obj), 'hello OR there, :you')

    def test_clean_init(self):
        clean = inputs.Clean('hello OR there, :you')
        self.assertEqual(clean.query_string, 'hello OR there, :you')
        self.assertEqual(clean.post_process, True)

    def test_clean_prepare(self):
        clean = inputs.Clean('hello OR there, :you')
        self.assertEqual(clean.prepare(self.query_obj), "hello or there, ':you'")

    def test_exact_init(self):
        exact = inputs.Exact('hello OR there, :you')
        self.assertEqual(exact.query_string, 'hello OR there, :you')
        self.assertEqual(exact.post_process, True)

    def test_exact_prepare(self):
        exact = inputs.Exact('hello OR there, :you')
        self.assertEqual(exact.prepare(self.query_obj), u'"hello OR there, :you"')

    def test_not_init(self):
        not_it = inputs.Not('hello OR there, :you')
        self.assertEqual(not_it.query_string, 'hello OR there, :you')
        self.assertEqual(not_it.post_process, True)

    def test_not_prepare(self):
        not_it = inputs.Not('hello OR there, :you')
        self.assertEqual(not_it.prepare(self.query_obj), u"NOT (hello or there, ':you')")

    def test_autoquery_init(self):
        autoquery = inputs.AutoQuery('panic -don\'t "froody dude"')
        self.assertEqual(autoquery.query_string, 'panic -don\'t "froody dude"')
        self.assertEqual(autoquery.post_process, False)

    def test_autoquery_prepare(self):
        autoquery = inputs.AutoQuery('panic -don\'t "froody dude"')
        self.assertEqual(autoquery.prepare(self.query_obj), u'panic NOT don\'t "froody dude"')

    def test_altparser_init(self):
        altparser = inputs.AltParser('dismax')
        self.assertEqual(altparser.parser_name, 'dismax')
        self.assertEqual(altparser.query_string, '')
        self.assertEqual(altparser.kwargs, {})
        self.assertEqual(altparser.post_process, False)

        altparser = inputs.AltParser('dismax', 'douglas adams', qf='author', mm=1)
        self.assertEqual(altparser.parser_name, 'dismax')
        self.assertEqual(altparser.query_string, 'douglas adams')
        self.assertEqual(altparser.kwargs, {'mm': 1, 'qf': 'author'})
        self.assertEqual(altparser.post_process, False)

    def test_altparser_prepare(self):
        altparser = inputs.AltParser('hello OR there, :you')
        # Not supported on that backend.
        self.assertEqual(altparser.prepare(self.query_obj), '')
