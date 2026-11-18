import warnings

from django.utils.encoding import force_str


class BaseInput:
    """
    The base input type. Doesn't do much. You want ``Raw`` instead.
    """

    input_type_name = "base"
    post_process = True

    def __init__(self, query_string, **kwargs):
        self.query_string = query_string
        self.kwargs = kwargs

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self)

    def __str__(self):
        return force_str(self.query_string)

    def prepare(self, query_obj):
        return self.query_string


class Raw(BaseInput):
    """
    An input type for passing a query directly to the backend.

    Prone to not being very portable.
    """

    input_type_name = "raw"
    post_process = False


class PythonData(BaseInput):
    """
    Represents a bare Python non-string type.

    Largely only for internal use.
    """

    input_type_name = "python_data"


class Clean(BaseInput):
    """
    An input type for sanitizing user/untrusted input.
    """

    input_type_name = "clean"

    def prepare(self, query_obj):
        query_string = super().prepare(query_obj)
        return query_obj.clean(query_string)


class Exact(BaseInput):
    """
    An input type for making exact matches.
    """

    input_type_name = "exact"

    def prepare(self, query_obj):
        query_string = super().prepare(query_obj)

        if self.kwargs.get("clean", False):
            # We need to clean each part of the exact match.
            exact_bits = [
                Clean(bit).prepare(query_obj) for bit in query_string.split(" ") if bit
            ]
            query_string = " ".join(exact_bits)

        return query_obj.build_exact_query(query_string)


class Not(Clean):
    """
    An input type for negating a query.
    """

    input_type_name = "not"

    def prepare(self, query_obj):
        query_string = super().prepare(query_obj)
        return query_obj.build_not_query(query_string)


class AutoQuery(BaseInput):
    """
    A convenience class that handles common user queries.

    In addition to cleaning all tokens, it handles double quote bits as
    exact matches & terms with '-' in front as NOT queries.

    The actual parsing and assembly is delegated to the backend's query
    class via ``build_auto_query()``, allowing backends to customize how
    the query string is constructed.
    """

    input_type_name = "auto_query"
    post_process = False

    def prepare(self, query_obj):
        query_string = super().prepare(query_obj)
        return query_obj.build_auto_query(query_string)


class AltParser(BaseInput):
    """
    If the engine supports it, this input type allows for submitting a query
    that uses a different parser.
    """

    input_type_name = "alt_parser"
    post_process = False
    use_parens = False

    def __init__(self, parser_name, query_string="", **kwargs):
        self.parser_name = parser_name
        self.query_string = query_string
        self.kwargs = kwargs

    def __repr__(self):
        return "<%s '%s' '%s' '%s'>" % (
            self.__class__.__name__,
            self.parser_name,
            self.query_string,
            self.kwargs,
        )

    def prepare(self, query_obj):
        if not hasattr(query_obj, "build_alt_parser_query"):
            warnings.warn(
                "Use of 'AltParser' input type is being ignored, as the '%s' backend doesn't support them."
                % query_obj
            )
            return ""

        return query_obj.build_alt_parser_query(
            self.parser_name, self.query_string, **self.kwargs
        )
