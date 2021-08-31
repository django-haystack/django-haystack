import re
from inspect import ismethod

from django.template import loader
from django.utils import datetime_safe

from haystack.exceptions import SearchFieldError
from haystack.utils import get_model_ct_tuple


class NOT_PROVIDED:
    pass


# Note that dates in the full ISO 8601 format will be accepted as long as the hour/minute/second components
# are zeroed for compatibility with search backends which lack a date time distinct from datetime:
DATE_REGEX = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(?:|T00:00:00Z?)$"
)
DATETIME_REGEX = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}).*?$"
)


# All the SearchFields variants.


class SearchField:
    """The base implementation of a search field."""

    field_type = None

    def __init__(
        self,
        model_attr=None,
        use_template=False,
        template_name=None,
        document=False,
        indexed=True,
        stored=True,
        faceted=False,
        default=NOT_PROVIDED,
        null=False,
        index_fieldname=None,
        facet_class=None,
        boost=1.0,
        weight=None,
        analyzer=None,
    ):
        # Track what the index thinks this field is called.
        self.instance_name = None
        self.model_attr = model_attr
        self.use_template = use_template
        self.template_name = template_name
        self.document = document
        self.indexed = indexed
        self.stored = stored
        self.faceted = faceted
        self._default = default
        self.null = null
        self.index_fieldname = index_fieldname
        self.boost = weight or boost
        self.analyzer = analyzer
        self.is_multivalued = False

        # We supply the facet_class for making it easy to create a faceted
        # field based off of this field.
        self.facet_class = facet_class

        if self.facet_class is None:
            self.facet_class = FacetCharField

        self.set_instance_name(None)

    def set_instance_name(self, instance_name):
        self.instance_name = instance_name

        if self.index_fieldname is None:
            self.index_fieldname = self.instance_name

    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self._default is not NOT_PROVIDED

    @property
    def default(self):
        """Returns the default value for the field."""
        if callable(self._default):
            return self._default()

        return self._default

    def prepare(self, obj):
        """
        Takes data from the provided object and prepares it for storage in the
        index.
        """
        # Give priority to a template.
        if self.use_template:
            return self.prepare_template(obj)
        elif self.model_attr is not None:
            attrs = self.split_model_attr_lookups()
            current_objects = [obj]

            values = self.resolve_attributes_lookup(current_objects, attrs)

            if len(values) == 1:
                return values[0]
            elif len(values) > 1:
                return values

        if self.has_default():
            return self.default
        else:
            return None

    def resolve_attributes_lookup(self, current_objects, attributes):
        """
        Recursive method that looks, for one or more objects, for an attribute that can be multiple
        objects (relations) deep.
        """
        values = []

        for current_object in current_objects:
            if not hasattr(current_object, attributes[0]):
                raise SearchFieldError(
                    "The model '%r' does not have a model_attr '%s'."
                    % (repr(current_object), attributes[0])
                )

            if len(attributes) > 1:
                current_objects_in_attr = self.get_iterable_objects(
                    getattr(current_object, attributes[0])
                )
                values.extend(
                    self.resolve_attributes_lookup(
                        current_objects_in_attr, attributes[1:]
                    )
                )
                continue

            current_object = getattr(current_object, attributes[0])

            if current_object is None:
                if self.has_default():
                    current_object = self._default
                elif self.null:
                    current_object = None
                else:
                    raise SearchFieldError(
                        "The model '%s' combined with model_attr '%s' returned None, but doesn't allow "
                        "a default or null value."
                        % (repr(current_object), self.model_attr)
                    )

            if callable(current_object):
                values.append(current_object())
            else:
                values.append(current_object)

        return values

    def split_model_attr_lookups(self):
        """Returns list of nested attributes for looking through the relation."""
        return self.model_attr.split("__")

    @classmethod
    def get_iterable_objects(cls, current_objects):
        """
        Returns iterable of objects that contain data. For example, resolves Django ManyToMany relationship
        so the attributes of the related models can then be accessed.
        """
        if current_objects is None:
            return []

        if hasattr(current_objects, "all"):
            # i.e, Django ManyToMany relationships
            if ismethod(current_objects.all):
                return current_objects.all()
            return []

        elif not hasattr(current_objects, "__iter__"):
            current_objects = [current_objects]

        return current_objects

    def prepare_template(self, obj):
        """
        Flattens an object for indexing.

        This loads a template
        (``search/indexes/{app_label}/{model_name}_{field_name}.txt``) and
        returns the result of rendering that template. ``object`` will be in
        its context.
        """
        if self.instance_name is None and self.template_name is None:
            raise SearchFieldError(
                "This field requires either its instance_name variable to be populated or an explicit template_name in order to load the correct template."
            )

        if self.template_name is not None:
            template_names = self.template_name

            if not isinstance(template_names, (list, tuple)):
                template_names = [template_names]
        else:
            app_label, model_name = get_model_ct_tuple(obj)
            template_names = [
                "search/indexes/%s/%s_%s.txt"
                % (app_label, model_name, self.instance_name)
            ]

        t = loader.select_template(template_names)
        return t.render({"object": obj})

    def convert(self, value):
        """
        Handles conversion between the data found and the type of the field.

        Extending classes should override this method and provide correct
        data coercion.
        """
        return value


class CharField(SearchField):
    field_type = "string"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetCharField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        return str(value)


class LocationField(SearchField):
    field_type = "location"

    def prepare(self, obj):
        from haystack.utils.geo import ensure_point

        value = super().prepare(obj)

        if value is None:
            return None

        pnt = ensure_point(value)
        pnt_lng, pnt_lat = pnt.coords
        return "%s,%s" % (pnt_lat, pnt_lng)

    def convert(self, value):
        from django.contrib.gis.geos import Point

        from haystack.utils.geo import ensure_point

        if value is None:
            return None

        if hasattr(value, "geom_type"):
            value = ensure_point(value)
            return value

        if isinstance(value, str):
            lat, lng = value.split(",")
        elif isinstance(value, (list, tuple)):
            # GeoJSON-alike
            lat, lng = value[1], value[0]
        elif isinstance(value, dict):
            lat = value.get("lat", 0)
            lng = value.get("lon", 0)
        else:
            raise TypeError("Unable to extract coordinates from %r" % value)

        value = Point(float(lng), float(lat))
        return value


class NgramField(CharField):
    field_type = "ngram"

    def __init__(self, **kwargs):
        if kwargs.get("faceted") is True:
            raise SearchFieldError("%s can not be faceted." % self.__class__.__name__)

        super().__init__(**kwargs)


class EdgeNgramField(NgramField):
    field_type = "edge_ngram"


class IntegerField(SearchField):
    field_type = "integer"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetIntegerField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        return int(value)


class FloatField(SearchField):
    field_type = "float"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetFloatField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        return float(value)


class DecimalField(SearchField):
    field_type = "string"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetDecimalField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        return str(value)


class BooleanField(SearchField):
    field_type = "boolean"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetBooleanField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        return bool(value)


class DateField(SearchField):
    field_type = "date"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetDateField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            match = DATE_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.date(
                    int(data["year"]), int(data["month"]), int(data["day"])
                )
            else:
                raise SearchFieldError(
                    "Date provided to '%s' field doesn't appear to be a valid date string: '%s'"
                    % (self.instance_name, value)
                )

        return value


class DateTimeField(SearchField):
    field_type = "datetime"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetDateTimeField

        super().__init__(**kwargs)

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            match = DATETIME_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.datetime(
                    int(data["year"]),
                    int(data["month"]),
                    int(data["day"]),
                    int(data["hour"]),
                    int(data["minute"]),
                    int(data["second"]),
                )
            else:
                raise SearchFieldError(
                    "Datetime provided to '%s' field doesn't appear to be a valid datetime string: '%s'"
                    % (self.instance_name, value)
                )

        return value


class MultiValueField(SearchField):
    field_type = "string"

    def __init__(self, **kwargs):
        if kwargs.get("facet_class") is None:
            kwargs["facet_class"] = FacetMultiValueField

        if kwargs.get("use_template") is True:
            raise SearchFieldError(
                "'%s' fields can not use templates to prepare their data."
                % self.__class__.__name__
            )

        super().__init__(**kwargs)
        self.is_multivalued = True

    def prepare(self, obj):
        return self.convert(super().prepare(obj))

    def convert(self, value):
        if value is None:
            return None

        if hasattr(value, "__iter__") and not isinstance(value, str):
            return value

        return [value]


class FacetField(SearchField):
    """
    ``FacetField`` is slightly different than the other fields because it can
    work in conjunction with other fields as its data source.

    Accepts an optional ``facet_for`` kwarg, which should be the field name
    (not ``index_fieldname``) of the field it should pull data from.
    """

    instance_name = None

    def __init__(self, **kwargs):
        handled_kwargs = self.handle_facet_parameters(kwargs)
        super().__init__(**handled_kwargs)

    def handle_facet_parameters(self, kwargs):
        if kwargs.get("faceted", False):
            raise SearchFieldError(
                "FacetField (%s) does not accept the 'faceted' argument."
                % self.instance_name
            )

        if not kwargs.get("null", True):
            raise SearchFieldError(
                "FacetField (%s) does not accept False for the 'null' argument."
                % self.instance_name
            )

        if not kwargs.get("indexed", True):
            raise SearchFieldError(
                "FacetField (%s) does not accept False for the 'indexed' argument."
                % self.instance_name
            )

        if kwargs.get("facet_class"):
            raise SearchFieldError(
                "FacetField (%s) does not accept the 'facet_class' argument."
                % self.instance_name
            )

        self.facet_for = None
        self.facet_class = None

        # Make sure the field is nullable.
        kwargs["null"] = True

        if "facet_for" in kwargs:
            self.facet_for = kwargs["facet_for"]
            del kwargs["facet_for"]

        return kwargs

    def get_facet_for_name(self):
        return self.facet_for or self.instance_name


class FacetCharField(FacetField, CharField):
    pass


class FacetIntegerField(FacetField, IntegerField):
    pass


class FacetFloatField(FacetField, FloatField):
    pass


class FacetDecimalField(FacetField, DecimalField):
    pass


class FacetBooleanField(FacetField, BooleanField):
    pass


class FacetDateField(FacetField, DateField):
    pass


class FacetDateTimeField(FacetField, DateTimeField):
    pass


class FacetMultiValueField(FacetField, MultiValueField):
    pass
