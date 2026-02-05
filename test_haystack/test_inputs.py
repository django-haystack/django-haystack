import re

from django.test import TestCase

from haystack import connections, inputs
from haystack.backends import BaseSearchQuery


class InputTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.query_obj = connections["default"].get_query()

    def test_raw_init(self):
        raw = inputs.Raw("hello OR there, :you")
        self.assertEqual(raw.query_string, "hello OR there, :you")
        self.assertEqual(raw.kwargs, {})
        self.assertEqual(raw.post_process, False)

        raw = inputs.Raw("hello OR there, :you", test="really")
        self.assertEqual(raw.query_string, "hello OR there, :you")
        self.assertEqual(raw.kwargs, {"test": "really"})
        self.assertEqual(raw.post_process, False)

    def test_raw_prepare(self):
        raw = inputs.Raw("hello OR there, :you")
        self.assertEqual(raw.prepare(self.query_obj), "hello OR there, :you")

    def test_clean_init(self):
        clean = inputs.Clean("hello OR there, :you")
        self.assertEqual(clean.query_string, "hello OR there, :you")
        self.assertEqual(clean.post_process, True)

    def test_clean_prepare(self):
        clean = inputs.Clean("hello OR there, :you")
        self.assertEqual(clean.prepare(self.query_obj), "hello OR there, :you")

    def test_exact_init(self):
        exact = inputs.Exact("hello OR there, :you")
        self.assertEqual(exact.query_string, "hello OR there, :you")
        self.assertEqual(exact.post_process, True)

    def test_exact_prepare(self):
        exact = inputs.Exact("hello OR there, :you")
        self.assertEqual(exact.prepare(self.query_obj), '"hello OR there, :you"')

        # Incorrect, but the backend doesn't implement much of anything useful.
        exact = inputs.Exact("hello OR there, :you", clean=True)
        self.assertEqual(exact.prepare(self.query_obj), '"hello OR there, :you"')

    def test_not_init(self):
        not_it = inputs.Not("hello OR there, :you")
        self.assertEqual(not_it.query_string, "hello OR there, :you")
        self.assertEqual(not_it.post_process, True)

    def test_not_prepare(self):
        not_it = inputs.Not("hello OR there, :you")
        self.assertEqual(not_it.prepare(self.query_obj), "NOT (hello OR there, :you)")

    def test_autoquery_init(self):
        autoquery = inputs.AutoQuery('panic -don\'t "froody dude"')
        self.assertEqual(autoquery.query_string, 'panic -don\'t "froody dude"')
        self.assertEqual(autoquery.post_process, False)

    def test_autoquery_prepare(self):
        autoquery = inputs.AutoQuery('panic -don\'t "froody dude"')
        self.assertEqual(
            autoquery.prepare(self.query_obj), 'panic NOT don\'t "froody dude"'
        )

    def test_altparser_init(self):
        altparser = inputs.AltParser("dismax")
        self.assertEqual(altparser.parser_name, "dismax")
        self.assertEqual(altparser.query_string, "")
        self.assertEqual(altparser.kwargs, {})
        self.assertEqual(altparser.post_process, False)

        altparser = inputs.AltParser("dismax", "douglas adams", qf="author", mm=1)
        self.assertEqual(altparser.parser_name, "dismax")
        self.assertEqual(altparser.query_string, "douglas adams")
        self.assertEqual(altparser.kwargs, {"mm": 1, "qf": "author"})
        self.assertEqual(altparser.post_process, False)

    def test_altparser_prepare(self):
        altparser = inputs.AltParser("dismax", "douglas adams", qf="author", mm=1)
        # Not supported on that backend.
        self.assertEqual(altparser.prepare(self.query_obj), "")


class BinaryNotSearchQuery(BaseSearchQuery):
    """
    A query class that treats NOT as a binary operator (like SQLite FTS5).

    In FTS5, NOT requires a left-hand operand:
        <query1> NOT <query2>

    This means negated terms must be collected and appended at the end
    as binary operators against the preceding positive query.
    """

    def build_auto_query(self, query_string):
        from haystack.inputs import Clean, Exact

        exact_match_re = re.compile(r'"(?P<phrase>.*?)"')
        exacts = exact_match_re.findall(query_string)
        tokens = []

        for rough_token in exact_match_re.split(query_string):
            if not rough_token:
                continue
            elif rough_token not in exacts:
                tokens.extend(rough_token.split(" "))
            else:
                tokens.append(rough_token)

        positive_bits = []
        negative_bits = []

        for token in tokens:
            if not token:
                continue
            if token in exacts:
                positive_bits.append(Exact(token, clean=True).prepare(self))
            elif token.startswith("-") and len(token) > 1:
                # Collect negated terms separately (without the NOT keyword)
                negative_bits.append(Clean(token[1:]).prepare(self))
            else:
                positive_bits.append(Clean(token).prepare(self))

        # Build FTS5-style query: positive terms first, then NOT as binary operator
        if positive_bits and negative_bits:
            return "({}) NOT ({})".format(
                " AND ".join(positive_bits), " AND ".join(negative_bits)
            )
        elif positive_bits:
            return " AND ".join(positive_bits)
        elif negative_bits:
            # FTS5 can't handle NOT without a positive term; return empty or raise
            return ""
        return ""


class BuildAutoQueryOverrideTestCase(TestCase):
    """
    Test that backends can override build_auto_query to customize
    how AutoQuery strings are parsed and assembled.

    This demonstrates the extensibility needed for backends like SQLite FTS5
    where NOT is a binary operator rather than unary.
    """

    def test_default_auto_query_uses_unary_not(self):
        """Default behavior: NOT is unary, applied inline to each negated term."""
        query_obj = connections["default"].get_query()
        autoquery = inputs.AutoQuery("foo bar -baz")
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, "foo bar NOT baz")

    def test_binary_not_override(self):
        """Custom backend can restructure query for binary NOT (FTS5-style)."""
        query_obj = BinaryNotSearchQuery()
        autoquery = inputs.AutoQuery("foo bar -baz")
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, "(foo AND bar) NOT (baz)")

    def test_binary_not_multiple_negations(self):
        """Multiple negated terms are grouped together."""
        query_obj = BinaryNotSearchQuery()
        autoquery = inputs.AutoQuery("foo -bar -baz")
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, "(foo) NOT (bar AND baz)")

    def test_binary_not_with_exact_phrase(self):
        """Exact phrases work with binary NOT."""
        query_obj = BinaryNotSearchQuery()
        autoquery = inputs.AutoQuery('"hello world" foo -bar')
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, '("hello world" AND foo) NOT (bar)')

    def test_binary_not_no_negations(self):
        """When no negations, just return positive terms."""
        query_obj = BinaryNotSearchQuery()
        autoquery = inputs.AutoQuery("foo bar")
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, "foo AND bar")

    def test_binary_not_only_negations(self):
        """FTS5 can't search for only negated terms; returns empty."""
        query_obj = BinaryNotSearchQuery()
        autoquery = inputs.AutoQuery("-foo -bar")
        result = autoquery.prepare(query_obj)
        self.assertEqual(result, "")
