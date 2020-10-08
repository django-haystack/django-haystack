from django.contrib.gis.measure import D
from django.test import TestCase

from haystack import connections
from haystack.exceptions import SpatialError
from haystack.query import SearchQuerySet
from haystack.utils.geo import (
    ensure_distance,
    ensure_geometry,
    ensure_point,
    ensure_wgs84,
    generate_bounding_box,
)

from .models import Checkin


class SpatialUtilitiesTestCase(TestCase):
    def test_ensure_geometry(self):
        from django.contrib.gis.geos import GEOSGeometry, Point

        self.assertRaises(
            SpatialError, ensure_geometry, [38.97127105172941, -95.23592948913574]
        )
        ensure_geometry(GEOSGeometry("POLYGON((-95 38, -96 40, -97 42, -95 38))"))
        ensure_geometry(GEOSGeometry("POINT(-95.23592948913574 38.97127105172941)"))
        ensure_geometry(Point(-95.23592948913574, 38.97127105172941))

    def test_ensure_point(self):
        from django.contrib.gis.geos import GEOSGeometry, Point

        self.assertRaises(
            SpatialError, ensure_point, [38.97127105172941, -95.23592948913574]
        )
        self.assertRaises(
            SpatialError,
            ensure_point,
            GEOSGeometry("POLYGON((-95 38, -96 40, -97 42, -95 38))"),
        )
        ensure_point(Point(-95.23592948913574, 38.97127105172941))

    def test_ensure_wgs84(self):
        from django.contrib.gis.geos import GEOSGeometry, Point

        self.assertRaises(
            SpatialError,
            ensure_wgs84,
            GEOSGeometry("POLYGON((-95 38, -96 40, -97 42, -95 38))"),
        )

        orig_pnt = Point(-95.23592948913574, 38.97127105172941)
        std_pnt = ensure_wgs84(orig_pnt)
        self.assertEqual(orig_pnt.srid, None)
        self.assertEqual(std_pnt.srid, 4326)
        self.assertEqual(std_pnt.x, -95.23592948913574)
        self.assertEqual(std_pnt.y, 38.97127105172941)

        orig_pnt = Point(-95.23592948913574, 38.97127105172941)
        orig_pnt.srid = 2805
        std_pnt = ensure_wgs84(orig_pnt)
        self.assertEqual(orig_pnt.srid, 2805)
        self.assertEqual(std_pnt.srid, 4326)
        # These should be different, since it got transformed.
        self.assertNotEqual(std_pnt.x, -95.23592948913574)
        self.assertNotEqual(std_pnt.y, 38.97127105172941)

    def test_ensure_distance(self):
        self.assertRaises(
            SpatialError, ensure_distance, [38.97127105172941, -95.23592948913574]
        )
        ensure_distance(D(mi=5))

    def test_generate_bounding_box(self):
        from django.contrib.gis.geos import Point

        downtown_bottom_left = Point(-95.23947, 38.9637903)
        downtown_top_right = Point(-95.23362278938293, 38.973081081164715)
        ((min_lat, min_lng), (max_lat, max_lng)) = generate_bounding_box(
            downtown_bottom_left, downtown_top_right
        )
        self.assertEqual(min_lat, 38.9637903)
        self.assertEqual(min_lng, -95.23947)
        self.assertEqual(max_lat, 38.973081081164715)
        self.assertEqual(max_lng, -95.23362278938293)

    def test_generate_bounding_box_crossing_line_date(self):
        from django.contrib.gis.geos import Point

        downtown_bottom_left = Point(95.23947, 38.9637903)
        downtown_top_right = Point(-95.23362278938293, 38.973081081164715)
        ((south, west), (north, east)) = generate_bounding_box(
            downtown_bottom_left, downtown_top_right
        )
        self.assertEqual(south, 38.9637903)
        self.assertEqual(west, 95.23947)
        self.assertEqual(north, 38.973081081164715)
        self.assertEqual(east, -95.23362278938293)


class SpatialSolrTestCase(TestCase):
    fixtures = ["sample_spatial_data.json"]
    using = "solr"

    def setUp(self):
        from django.contrib.gis.geos import Point

        super().setUp()
        self.ui = connections[self.using].get_unified_index()
        self.checkindex = self.ui.get_index(Checkin)
        self.checkindex.reindex(using=self.using)
        self.sqs = SearchQuerySet().using(self.using)

        self.downtown_pnt = Point(-95.23592948913574, 38.97127105172941)
        self.downtown_bottom_left = Point(-95.23947, 38.9637903)
        self.downtown_top_right = Point(-95.23362278938293, 38.973081081164715)
        self.lawrence_bottom_left = Point(-95.345535, 39.002643)
        self.lawrence_top_right = Point(-95.202713, 38.923626)

    def tearDown(self):
        self.checkindex.clear(using=self.using)
        super().setUp()

    def test_indexing(self):
        # Make sure the indexed data looks correct.
        first = Checkin.objects.get(pk=1)
        sqs = self.sqs.models(Checkin).filter(django_id=first.pk)
        self.assertEqual(sqs.count(), 1)
        self.assertEqual(sqs[0].username, first.username)
        # Make sure we've got a proper ``Point`` object.
        self.assertAlmostEqual(sqs[0].location.coords[0], first.longitude)
        self.assertAlmostEqual(sqs[0].location.coords[1], first.latitude)

        # Double-check, to make sure there was nothing accidentally copied
        # between instances.
        second = Checkin.objects.get(pk=2)
        self.assertNotEqual(second.latitude, first.latitude)
        sqs = self.sqs.models(Checkin).filter(django_id=second.pk)
        self.assertEqual(sqs.count(), 1)
        self.assertEqual(sqs[0].username, second.username)
        self.assertAlmostEqual(sqs[0].location.coords[0], second.longitude)
        self.assertAlmostEqual(sqs[0].location.coords[1], second.latitude)

    def test_within(self):
        self.assertEqual(self.sqs.all().count(), 10)

        sqs = self.sqs.within(
            "location", self.downtown_bottom_left, self.downtown_top_right
        )
        self.assertEqual(sqs.count(), 7)

        sqs = self.sqs.within(
            "location", self.lawrence_bottom_left, self.lawrence_top_right
        )
        self.assertEqual(sqs.count(), 9)

    def test_dwithin(self):
        self.assertEqual(self.sqs.all().count(), 10)

        sqs = self.sqs.dwithin("location", self.downtown_pnt, D(mi=0.1))
        self.assertEqual(sqs.count(), 5)

        sqs = self.sqs.dwithin("location", self.downtown_pnt, D(mi=0.5))
        self.assertEqual(sqs.count(), 7)

        sqs = self.sqs.dwithin("location", self.downtown_pnt, D(mi=100))
        self.assertEqual(sqs.count(), 10)

    def test_distance_added(self):
        sqs = self.sqs.within(
            "location", self.downtown_bottom_left, self.downtown_top_right
        ).distance("location", self.downtown_pnt)
        self.assertEqual(sqs.count(), 7)
        self.assertAlmostEqual(sqs[0].distance.mi, 0.01985226)
        self.assertAlmostEqual(sqs[1].distance.mi, 0.03385863)
        self.assertAlmostEqual(sqs[2].distance.mi, 0.04539100)
        self.assertAlmostEqual(sqs[3].distance.mi, 0.04831436)
        self.assertAlmostEqual(sqs[4].distance.mi, 0.41116546)
        self.assertAlmostEqual(sqs[5].distance.mi, 0.25098114)
        self.assertAlmostEqual(sqs[6].distance.mi, 0.04831436)

        sqs = self.sqs.dwithin("location", self.downtown_pnt, D(mi=0.1)).distance(
            "location", self.downtown_pnt
        )
        self.assertEqual(sqs.count(), 5)
        self.assertAlmostEqual(sqs[0].distance.mi, 0.01985226)
        self.assertAlmostEqual(sqs[1].distance.mi, 0.03385863)
        self.assertAlmostEqual(sqs[2].distance.mi, 0.04539100)
        self.assertAlmostEqual(sqs[3].distance.mi, 0.04831436)
        self.assertAlmostEqual(sqs[4].distance.mi, 0.04831436)

    def test_order_by_distance(self):
        sqs = (
            self.sqs.within(
                "location", self.downtown_bottom_left, self.downtown_top_right
            )
            .distance("location", self.downtown_pnt)
            .order_by("distance")
        )
        self.assertEqual(sqs.count(), 7)
        self.assertEqual(
            [result.pk for result in sqs], ["8", "9", "6", "3", "1", "2", "5"]
        )
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0199", "0.0339", "0.0454", "0.0483", "0.0483", "0.2510", "0.4112"],
        )

        sqs = (
            self.sqs.dwithin("location", self.downtown_pnt, D(mi=0.1))
            .distance("location", self.downtown_pnt)
            .order_by("distance")
        )
        self.assertEqual(sqs.count(), 5)
        self.assertEqual([result.pk for result in sqs], ["8", "9", "6", "3", "1"])
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0199", "0.0339", "0.0454", "0.0483", "0.0483"],
        )

        sqs = (
            self.sqs.dwithin("location", self.downtown_pnt, D(mi=0.1))
            .distance("location", self.downtown_pnt)
            .order_by("-distance")
        )
        self.assertEqual(sqs.count(), 5)
        self.assertEqual([result.pk for result in sqs], ["3", "1", "6", "9", "8"])
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0483", "0.0483", "0.0454", "0.0339", "0.0199"],
        )

    def test_complex(self):
        sqs = (
            self.sqs.auto_query("coffee")
            .within("location", self.downtown_bottom_left, self.downtown_top_right)
            .distance("location", self.downtown_pnt)
            .order_by("distance")
        )
        self.assertEqual(sqs.count(), 5)
        self.assertEqual([result.pk for result in sqs], ["8", "6", "3", "1", "2"])
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0199", "0.0454", "0.0483", "0.0483", "0.2510"],
        )

        sqs = (
            self.sqs.auto_query("coffee")
            .dwithin("location", self.downtown_pnt, D(mi=0.1))
            .distance("location", self.downtown_pnt)
            .order_by("distance")
        )
        self.assertEqual(sqs.count(), 4)
        self.assertEqual([result.pk for result in sqs], ["8", "6", "3", "1"])
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0199", "0.0454", "0.0483", "0.0483"],
        )

        sqs = (
            self.sqs.auto_query("coffee")
            .dwithin("location", self.downtown_pnt, D(mi=0.1))
            .distance("location", self.downtown_pnt)
            .order_by("-distance")
        )
        self.assertEqual(sqs.count(), 4)
        self.assertEqual([result.pk for result in sqs], ["3", "1", "6", "8"])
        self.assertEqual(
            ["%0.04f" % result.distance.mi for result in sqs],
            ["0.0483", "0.0483", "0.0454", "0.0199"],
        )

        sqs = (
            self.sqs.auto_query("coffee")
            .within("location", self.downtown_bottom_left, self.downtown_top_right)
            .distance("location", self.downtown_pnt)
            .order_by("-created")
        )
        self.assertEqual(sqs.count(), 5)
        self.assertEqual([result.pk for result in sqs], ["8", "6", "3", "2", "1"])

        sqs = (
            self.sqs.auto_query("coffee")
            .dwithin("location", self.downtown_pnt, D(mi=0.1))
            .distance("location", self.downtown_pnt)
            .order_by("-created")
        )
        self.assertEqual(sqs.count(), 4)
        self.assertEqual([result.pk for result in sqs], ["8", "6", "3", "1"])
