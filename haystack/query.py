import operator
import warnings
from functools import reduce

from haystack import connection_router, connections
from haystack.backends import SQ
from haystack.constants import DEFAULT_OPERATOR, ITERATOR_LOAD_PER_QUERY
from haystack.exceptions import NotHandled
from haystack.inputs import AutoQuery, Raw
from haystack.utils import log as logging


class SearchQuerySet:
    """
    Provides a way to specify search parameters and lazily load results.

    Supports chaining (a la QuerySet) to narrow the search.
    """

    def __init__(self, using=None, query=None):
        # ``_using`` should only ever be a value other than ``None`` if it's
        # been forced with the ``.using`` method.
        self._using = using
        self.query = None
        self._determine_backend()

        # If ``query`` is present, it should override even what the routers
        # think.
        if query is not None:
            self.query = query

        self._result_cache = []
        self._result_count = None
        self._cache_full = False
        self._load_all = False
        self._ignored_result_count = 0
        self.log = logging.getLogger("haystack")

    def _determine_backend(self):
        # A backend has been manually selected. Use it instead.
        if self._using is not None:
            self.query = connections[self._using].get_query()
            return

        # No backend, so rely on the routers to figure out what's right.
        hints = {}

        if self.query:
            hints["models"] = self.query.models

        backend_alias = connection_router.for_read(**hints)

        # The ``SearchQuery`` might swap itself out for a different variant
        # here.
        if self.query:
            self.query = self.query.using(backend_alias)
        else:
            self.query = connections[backend_alias].get_query()

    def __getstate__(self):
        """
        For pickling.
        """
        len(self)
        obj_dict = self.__dict__.copy()
        obj_dict["_iter"] = None
        obj_dict["log"] = None
        return obj_dict

    def __setstate__(self, data_dict):
        """
        For unpickling.
        """
        self.__dict__ = data_dict
        self.log = logging.getLogger("haystack")

    def __repr__(self):
        return "<SearchQuerySet: query=%r, using=%r>" % (self.query, self._using)

    def __len__(self):
        if self._result_count is None:
            self._result_count = self.query.get_count()

            # Some backends give weird, false-y values here. Convert to zero.
            if not self._result_count:
                self._result_count = 0

        # This needs to return the actual number of hits, not what's in the cache.
        return self._result_count - self._ignored_result_count

    def __iter__(self):
        if self._cache_is_full():
            # We've got a fully populated cache. Let Python do the hard work.
            return iter(self._result_cache)

        return self._manual_iter()

    def __and__(self, other):
        if isinstance(other, EmptySearchQuerySet):
            return other._clone()
        combined = self._clone()
        combined.query.combine(other.query, SQ.AND)
        return combined

    def __or__(self, other):
        combined = self._clone()
        if isinstance(other, EmptySearchQuerySet):
            return combined
        combined.query.combine(other.query, SQ.OR)
        return combined

    def _cache_is_full(self):
        if not self.query.has_run():
            return False

        if len(self) <= 0:
            return True

        try:
            self._result_cache.index(None)
            return False
        except ValueError:
            # No ``None``s found in the results. Check the length of the cache.
            return len(self._result_cache) > 0

    def _manual_iter(self):
        # If we're here, our cache isn't fully populated.
        # For efficiency, fill the cache as we go if we run out of results.
        # Also, this can't be part of the __iter__ method due to Python's rules
        # about generator functions.
        current_position = 0
        current_cache_max = 0

        while True:
            if len(self._result_cache) > 0:
                try:
                    current_cache_max = self._result_cache.index(None)
                except ValueError:
                    current_cache_max = len(self._result_cache)

            while current_position < current_cache_max:
                yield self._result_cache[current_position]
                current_position += 1

            if self._cache_is_full():
                return

            # We've run out of results and haven't hit our limit.
            # Fill more of the cache.
            if not self._fill_cache(
                current_position, current_position + ITERATOR_LOAD_PER_QUERY
            ):
                return

    def post_process_results(self, results):
        to_cache = []

        # Check if we wish to load all objects.
        if self._load_all:
            models_pks = {}
            loaded_objects = {}

            # Remember the search position for each result so we don't have to resort later.
            for result in results:
                models_pks.setdefault(result.model, []).append(result.pk)

            # Load the objects for each model in turn.
            for model in models_pks:
                loaded_objects[model] = self._load_model_objects(
                    model, models_pks[model]
                )

        for result in results:
            if self._load_all:

                model_objects = loaded_objects.get(result.model, {})
                # Try to coerce a primary key object that matches the models pk
                # We have to deal with semi-arbitrary keys being cast from strings (UUID, int, etc)
                if model_objects:
                    result_klass = type(next(iter(model_objects)))
                    result.pk = result_klass(result.pk)

                    try:
                        result._object = model_objects[result.pk]
                    except KeyError:
                        # The object was either deleted since we indexed or should
                        # be ignored for other reasons such as an overriden 'load_all_queryset';
                        # fail silently.
                        self._ignored_result_count += 1

                        # avoid an unfilled None at the end of the result cache
                        self._result_cache.pop()
                        continue
                else:
                    # No objects were returned -- possible due to SQS nesting such as
                    # XYZ.objects.filter(id__gt=10) where the amount ignored are
                    # exactly equal to the ITERATOR_LOAD_PER_QUERY
                    del self._result_cache[: len(results)]
                    self._ignored_result_count += len(results)
                    break

            to_cache.append(result)

        return to_cache

    def _load_model_objects(self, model, pks):
        try:
            ui = connections[self.query._using].get_unified_index()
            index = ui.get_index(model)
            objects = index.read_queryset(using=self.query._using)
            return objects.in_bulk(pks)
        except NotHandled:
            self.log.warning("Model '%s' not handled by the routers.", model)
            # Revert to old behaviour
            return model._default_manager.in_bulk(pks)

    def _fill_cache(self, start, end, **kwargs):
        # Tell the query where to start from and how many we'd like.
        self.query._reset()

        if start is None:
            start = 0

        query_start = start
        query_start += self._ignored_result_count
        query_end = end
        if query_end is not None:
            query_end += self._ignored_result_count

        self.query.set_limits(query_start, query_end)
        results = self.query.get_results(**kwargs)

        if results is None or len(results) == 0:
            # trim missing stuff from the result cache
            self._result_cache = self._result_cache[:start]
            return False

        # Setup the full cache now that we know how many results there are.
        # We need the ``None``s as placeholders to know what parts of the
        # cache we have/haven't filled.
        # Using ``None`` like this takes up very little memory. In testing,
        # an array of 100,000 ``None``s consumed less than .5 Mb, which ought
        # to be an acceptable loss for consistent and more efficient caching.
        if len(self._result_cache) == 0:
            self._result_cache = [None] * self.query.get_count()

        fill_start, fill_end = start, end
        if fill_end is None:
            fill_end = self.query.get_count()
        cache_start = fill_start

        while True:
            to_cache = self.post_process_results(results)

            # Assign by slice.
            self._result_cache[cache_start : cache_start + len(to_cache)] = to_cache

            if None in self._result_cache[start:end]:
                fill_start = fill_end
                fill_end += ITERATOR_LOAD_PER_QUERY
                cache_start += len(to_cache)

                # Tell the query where to start from and how many we'd like.
                self.query._reset()
                self.query.set_limits(fill_start, fill_end)
                results = self.query.get_results()

                if results is None or len(results) == 0:
                    # No more results. Trim missing stuff from the result cache
                    self._result_cache = self._result_cache[:cache_start]
                    break
            else:
                break

        return True

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int)):
            raise TypeError
        assert (not isinstance(k, slice) and (k >= 0)) or (
            isinstance(k, slice)
            and (k.start is None or k.start >= 0)
            and (k.stop is None or k.stop >= 0)
        ), "Negative indexing is not supported."

        # Remember if it's a slice or not. We're going to treat everything as
        # a slice to simply the logic and will `.pop()` at the end as needed.
        if isinstance(k, slice):
            is_slice = True
            start = k.start

            if k.stop is not None:
                bound = int(k.stop)
            else:
                bound = None
        else:
            is_slice = False
            start = k
            bound = k + 1

        # We need check to see if we need to populate more of the cache.
        if len(self._result_cache) <= 0 or (
            None in self._result_cache[start:bound] and not self._cache_is_full()
        ):
            try:
                self._fill_cache(start, bound)
            except StopIteration:
                # There's nothing left, even though the bound is higher.
                pass

        # Cache should be full enough for our needs.
        if is_slice:
            return self._result_cache[start:bound]
        else:
            return self._result_cache[start]

    # Methods that return a SearchQuerySet.
    def all(self):  # noqa A003
        """Returns all results for the query."""
        return self._clone()

    def none(self):
        """Returns an empty result list for the query."""
        return self._clone(klass=EmptySearchQuerySet)

    def filter(self, *args, **kwargs):  # noqa A003
        """Narrows the search based on certain attributes and the default operator."""
        if DEFAULT_OPERATOR == "OR":
            return self.filter_or(*args, **kwargs)
        else:
            return self.filter_and(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        clone.query.add_filter(~SQ(*args, **kwargs))
        return clone

    def filter_and(self, *args, **kwargs):
        """Narrows the search by looking for (and including) certain attributes."""
        clone = self._clone()
        clone.query.add_filter(SQ(*args, **kwargs))
        return clone

    def filter_or(self, *args, **kwargs):
        """Narrows the search by ensuring certain attributes are not included."""
        clone = self._clone()
        clone.query.add_filter(SQ(*args, **kwargs), use_or=True)
        return clone

    def order_by(self, *args):
        """Alters the order in which the results should appear."""
        clone = self._clone()

        for field in args:
            clone.query.add_order_by(field)

        return clone

    def highlight(self, **kwargs):
        """Adds highlighting to the results."""
        clone = self._clone()
        clone.query.add_highlight(**kwargs)
        return clone

    def models(self, *models):
        """Accepts an arbitrary number of Model classes to include in the search."""
        clone = self._clone()

        for model in models:
            if (
                model
                not in connections[self.query._using]
                .get_unified_index()
                .get_indexed_models()
            ):
                warnings.warn("The model %r is not registered for search." % (model,))

            clone.query.add_model(model)

        return clone

    def result_class(self, klass):
        """
        Allows specifying a different class to use for results.

        Overrides any previous usages. If ``None`` is provided, Haystack will
        revert back to the default ``SearchResult`` object.
        """
        clone = self._clone()
        clone.query.set_result_class(klass)
        return clone

    def boost(self, term, boost):
        """Boosts a certain aspect of the query."""
        clone = self._clone()
        clone.query.add_boost(term, boost)
        return clone

    def facet(self, field, **options):
        """Adds faceting to a query for the provided field."""
        clone = self._clone()
        clone.query.add_field_facet(field, **options)
        return clone

    def within(self, field, point_1, point_2):
        """Spatial: Adds a bounding box search to the query."""
        clone = self._clone()
        clone.query.add_within(field, point_1, point_2)
        return clone

    def dwithin(self, field, point, distance):
        """Spatial: Adds a distance-based search to the query."""
        clone = self._clone()
        clone.query.add_dwithin(field, point, distance)
        return clone

    def stats(self, field):
        """Adds stats to a query for the provided field."""
        return self.stats_facet(field, facet_fields=None)

    def stats_facet(self, field, facet_fields=None):
        """Adds stats facet for the given field and facet_fields represents
        the faceted fields."""
        clone = self._clone()
        stats_facets = []
        try:
            stats_facets.append(sum(facet_fields, []))
        except TypeError:
            if facet_fields:
                stats_facets.append(facet_fields)
        clone.query.add_stats_query(field, stats_facets)
        return clone

    def distance(self, field, point):
        """
        Spatial: Denotes results must have distance measurements from the
        provided point.
        """
        clone = self._clone()
        clone.query.add_distance(field, point)
        return clone

    def date_facet(self, field, start_date, end_date, gap_by, gap_amount=1):
        """Adds faceting to a query for the provided field by date."""
        clone = self._clone()
        clone.query.add_date_facet(
            field, start_date, end_date, gap_by, gap_amount=gap_amount
        )
        return clone

    def query_facet(self, field, query):
        """Adds faceting to a query for the provided field with a custom query."""
        clone = self._clone()
        clone.query.add_query_facet(field, query)
        return clone

    def narrow(self, query):
        """Pushes existing facet choices into the search."""

        if isinstance(query, SQ):
            # produce query string using empty query of the same class
            empty_query = self.query._clone()
            empty_query._reset()
            query = query.as_query_string(empty_query.build_query_fragment)

        clone = self._clone()
        clone.query.add_narrow_query(query)
        return clone

    def raw_search(self, query_string, **kwargs):
        """Passes a raw query directly to the backend."""
        return self.filter(content=Raw(query_string, **kwargs))

    def load_all(self):
        """Efficiently populates the objects in the search results."""
        clone = self._clone()
        clone._load_all = True
        return clone

    def auto_query(self, query_string, fieldname="content"):
        """
        Performs a best guess constructing the search query.

        This method is somewhat naive but works well enough for the simple,
        common cases.
        """
        kwargs = {fieldname: AutoQuery(query_string)}
        return self.filter(**kwargs)

    def autocomplete(self, **kwargs):
        """
        A shortcut method to perform an autocomplete search.

        Must be run against fields that are either ``NgramField`` or
        ``EdgeNgramField``.
        """
        clone = self._clone()
        query_bits = []

        for field_name, query in kwargs.items():
            for word in query.split(" "):
                bit = clone.query.clean(word.strip())
                if bit:
                    kwargs = {field_name: bit}
                    query_bits.append(SQ(**kwargs))

        return clone.filter(reduce(operator.__and__, query_bits))

    def using(self, connection_name):
        """
        Allows switching which connection the ``SearchQuerySet`` uses to
        search in.
        """
        clone = self._clone()
        clone.query = self.query.using(connection_name)
        clone._using = connection_name
        return clone

    # Methods that do not return a SearchQuerySet.

    def count(self):
        """Returns the total number of matching results."""
        return len(self)

    def best_match(self):
        """Returns the best/top search result that matches the query."""
        return self[0]

    def latest(self, date_field):
        """Returns the most recent search result that matches the query."""
        clone = self._clone()
        clone.query.clear_order_by()
        clone.query.add_order_by("-%s" % date_field)
        return clone.best_match()

    def more_like_this(self, model_instance):
        """Finds similar results to the object passed in."""
        clone = self._clone()
        clone.query.more_like_this(model_instance)
        return clone

    def facet_counts(self):
        """
        Returns the facet counts found by the query.

        This will cause the query to execute and should generally be used when
        presenting the data.
        """
        if self.query.has_run():
            return self.query.get_facet_counts()
        else:
            clone = self._clone()
            return clone.query.get_facet_counts()

    def stats_results(self):
        """
        Returns the stats results found by the query.
        """
        if self.query.has_run():
            return self.query.get_stats()
        else:
            clone = self._clone()
            return clone.query.get_stats()

    def set_spelling_query(self, spelling_query):
        """Set the exact text to be used to generate spelling suggestions

        When making complicated queries, such as the alt parser mechanism
        used by Solr dismax/edismax, this provides a convenient way to set
        the a simple text string which will be used to generate spelling
        suggestions without including unnecessary syntax.
        """
        clone = self._clone()
        clone.query.set_spelling_query(spelling_query)
        return clone

    def spelling_suggestion(self, preferred_query=None):
        """
        Returns the spelling suggestion found by the query.

        To work, you must set ``INCLUDE_SPELLING`` within your connection's
        settings dictionary to ``True``. Otherwise, ``None`` will be returned.

        This will cause the query to execute and should generally be used when
        presenting the data.
        """
        if self.query.has_run():
            return self.query.get_spelling_suggestion(preferred_query)
        else:
            clone = self._clone()
            return clone.query.get_spelling_suggestion(preferred_query)

    def values(self, *fields):
        """
        Returns a list of dictionaries, each containing the key/value pairs for
        the result, exactly like Django's ``ValuesQuerySet``.
        """
        qs = self._clone(klass=ValuesSearchQuerySet)
        qs._fields.extend(fields)
        return qs

    def values_list(self, *fields, **kwargs):
        """
        Returns a list of field values as tuples, exactly like Django's
        ``QuerySet.values``.

        Optionally accepts a ``flat=True`` kwarg, which in the case of a
        single field being provided, will return a flat list of that field
        rather than a list of tuples.
        """
        flat = kwargs.pop("flat", False)

        if flat and len(fields) > 1:
            raise TypeError(
                "'flat' is not valid when values_list is called with more than one field."
            )

        qs = self._clone(klass=ValuesListSearchQuerySet)
        qs._fields.extend(fields)
        qs._flat = flat
        return qs

    # Utility methods.

    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__

        query = self.query._clone()
        clone = klass(query=query)
        clone._load_all = self._load_all
        return clone


class EmptySearchQuerySet(SearchQuerySet):
    """
    A stubbed SearchQuerySet that behaves as normal but always returns no
    results.
    """

    def __len__(self):
        return 0

    def _cache_is_full(self):
        # Pretend the cache is always full with no results.
        return True

    def _clone(self, klass=None):
        clone = super()._clone(klass=klass)
        clone._result_cache = []
        return clone

    def _fill_cache(self, start, end):
        return False

    def facet_counts(self):
        return {}


class ValuesListSearchQuerySet(SearchQuerySet):
    """
    A ``SearchQuerySet`` which returns a list of field values as tuples, exactly
    like Django's ``ValuesListQuerySet``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flat = False
        self._fields = []

        # Removing this dependency would require refactoring much of the backend
        # code (_process_results, etc.) and these aren't large enough to make it
        # an immediate priority:
        self._internal_fields = ["id", "django_ct", "django_id", "score"]

    def _clone(self, klass=None):
        clone = super()._clone(klass=klass)
        clone._fields = self._fields
        clone._flat = self._flat
        return clone

    def _fill_cache(self, start, end):
        query_fields = set(self._internal_fields)
        query_fields.update(self._fields)
        kwargs = {"fields": query_fields}
        return super()._fill_cache(start, end, **kwargs)

    def post_process_results(self, results):
        to_cache = []

        if self._flat:
            accum = to_cache.extend
        else:
            accum = to_cache.append

        for result in results:
            accum([getattr(result, i, None) for i in self._fields])

        return to_cache


class ValuesSearchQuerySet(ValuesListSearchQuerySet):
    """
    A ``SearchQuerySet`` which returns a list of dictionaries, each containing
    the key/value pairs for the result, exactly like Django's
    ``ValuesQuerySet``.
    """

    def _fill_cache(self, start, end):
        query_fields = set(self._internal_fields)
        query_fields.update(self._fields)
        kwargs = {"fields": query_fields}
        return super(ValuesListSearchQuerySet, self)._fill_cache(start, end, **kwargs)

    def post_process_results(self, results):
        to_cache = []

        for result in results:
            to_cache.append({i: getattr(result, i, None) for i in self._fields})

        return to_cache


class RelatedSearchQuerySet(SearchQuerySet):
    """
    A variant of the SearchQuerySet that can handle `load_all_queryset`s.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_all_querysets = {}
        self._result_cache = []

    def _load_model_objects(self, model, pks):
        if model in self._load_all_querysets:
            # Use the overriding queryset.
            return self._load_all_querysets[model].in_bulk(pks)
        else:
            # Check the SearchIndex for the model for an override.

            try:
                ui = connections[self.query._using].get_unified_index()
                index = ui.get_index(model)
                qs = index.load_all_queryset()
                return qs.in_bulk(pks)
            except NotHandled:
                # The model returned doesn't seem to be handled by the
                # routers. We should silently fail and populate
                # nothing for those objects.
                return {}

    def load_all_queryset(self, model, queryset):
        """
        Allows for specifying a custom ``QuerySet`` that changes how ``load_all``
        will fetch records for the provided model.

        This is useful for post-processing the results from the query, enabling
        things like adding ``select_related`` or filtering certain data.
        """
        clone = self._clone()
        clone._load_all_querysets[model] = queryset
        return clone

    def _clone(self, klass=None):
        clone = super()._clone(klass=klass)
        clone._load_all_querysets = self._load_all_querysets
        return clone
