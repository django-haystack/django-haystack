.. _ref-spatial:

==============
Spatial Search
==============

Spatial search (also called geospatial search) allows you to take data that
has a geographic location & enhance the search results by limiting them to a
physical area. Haystack, combined with the latest versions of a couple engines,
can provide this type of search.

In addition, Haystack tries to implement these features in a way that is as
close to GeoDjango_ as possible. There are some differences, which we'll
highlight throughout this guide. Additionally, while the support isn't as
comprehensive as PostGIS (for example), it is still quite useful.

.. _GeoDjango: https://docs.djangoproject.com/en/1.11/ref/contrib/gis/


Additional Requirements
=======================

The spatial functionality has only one non-included, non-available-in-Django
dependency:

* ``geopy`` - ``pip install geopy``

If you do not ever need distance information, you may be able to skip
installing ``geopy``.


Support
=======

You need the latest & greatest of either Solr or Elasticsearch. None of the
other backends (specifically the engines) support this kind of search.

For Solr_, you'll need at least **v3.5+**. In addition, if you have an existing
install of Haystack & Solr, you'll need to upgrade the schema & reindex your
data. If you're adding geospatial data, you would have to reindex anyhow.

For Elasticsearch, you'll need at least v0.17.7, preferably v0.18.6 or better.
If you're adding geospatial data, you'll have to reindex as well.

.. _Solr: http://lucene.apache.org/solr/

====================== ====== =============== ======== ======== ======
Lookup Type            Solr   Elasticsearch   Whoosh   Xapian   Simple
====================== ====== =============== ======== ======== ======
`within`               X      X
`dwithin`              X      X
`distance`             X      X
`order_by('distance')` X      X
`polygon`                     X
====================== ====== =============== ======== ======== ======

For more details, you can inspect http://wiki.apache.org/solr/SpatialSearch
or http://www.elasticsearch.org/guide/reference/query-dsl/geo-bounding-box-filter.html.


Geospatial Assumptions
======================

``Points``
----------

Haystack prefers to work with ``Point`` objects, which are located in
``django.contrib.gis.geos.Point``.

``Point`` objects use **LONGITUDE, LATITUDE** for their construction, regardless
if you use the parameters to instantiate them or WKT_/``GEOSGeometry``.

.. _WKT: http://en.wikipedia.org/wiki/Well-known_text

Examples::

    # Using positional arguments.
    from django.contrib.gis.geos import Point
    pnt = Point(-95.23592948913574, 38.97127105172941)

    # Using WKT.
    from django.contrib.gis.geos import GEOSGeometry
    pnt = GEOSGeometry('POINT(-95.23592948913574 38.97127105172941)')

They are preferred over just providing ``latitude, longitude`` because they are
more intelligent, have a spatial reference system attached & are more consistent
with GeoDjango's use.


``Distance``
------------

Haystack also uses the ``D`` (or ``Distance``) objects from GeoDjango,
implemented in ``django.contrib.gis.measure.Distance``.

``Distance`` objects accept a very flexible set of measurements during
instantiaton and can convert amongst them freely. This is important, because
the engines rely on measurements being in kilometers but you're free to use
whatever units you want.

Examples::

    from django.contrib.gis.measure import D

    # Start at 5 miles.
    imperial_d = D(mi=5)

    # Convert to fathoms...
    fathom_d = imperial_d.fathom

    # Now to kilometers...
    km_d = imperial_d.km

    # And back to miles.
    mi = imperial_d.mi

They are preferred over just providing a raw distance because they are
more intelligent, have a well-defined unit system attached & are consistent
with GeoDjango's use.


``WGS-84``
----------

All engines assume WGS-84 (SRID 4326). At the time of writing, there does **not**
appear to be a way to switch this. Haystack will transform all points into this
coordinate system for you.


Indexing
========

Indexing is relatively simple. Simply add a ``LocationField`` (or several)
onto your ``SearchIndex`` class(es) & provide them a ``Point`` object. For
example::

    from haystack import indexes
    from shops.models import Shop


    class ShopIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        # ... the usual, then...
        location = indexes.LocationField(model_attr='coordinates')

        def get_model(self):
            return Shop

If you must manually prepare the data, you have to do something slightly less
convenient, returning a string-ified version of the coordinates in WGS-84 as
``lat,long``::

    from haystack import indexes
    from shops.models import Shop


    class ShopIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        # ... the usual, then...
        location = indexes.LocationField()

        def get_model(self):
            return Shop

        def prepare_location(self, obj):
            # If you're just storing the floats...
            return "%s,%s" % (obj.latitude, obj.longitude)

Alternatively, you could build a method/property onto the ``Shop`` model that
returns a ``Point`` based on those coordinates::

    # shops/models.py
    from django.contrib.gis.geos import Point
    from django.db import models


    class Shop(models.Model):
        # ... the usual, then...
        latitude = models.FloatField()
        longitude = models.FloatField()

        # Usual methods, then...
        def get_location(self):
            # Remember, longitude FIRST!
            return Point(self.longitude, self.latitude)


    # shops/search_indexes.py
    from haystack import indexes
    from shops.models import Shop


    class ShopIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        location = indexes.LocationField(model_attr='get_location')

        def get_model(self):
            return Shop


Querying
========

There are two types of geospatial queries you can run, ``within`` & ``dwithin``.
Like their GeoDjango counterparts (within_ & dwithin_), these methods focus on
finding results within an area.

.. _within: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#within
.. _dwithin: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#dwithin


``within``
----------

.. method:: SearchQuerySet.within(self, field, point_1, point_2)

``within`` is a bounding box comparison. A bounding box is a rectangular area
within which to search. It's composed of a bottom-left point & a top-right
point. It is faster but slighty sloppier than its counterpart.

Examples::

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point

    downtown_bottom_left = Point(-95.23947, 38.9637903)
    downtown_top_right = Point(-95.23362278938293, 38.973081081164715)

    # 'location' is the fieldname from our ``SearchIndex``...

    # Do the bounding box query.
    sqs = SearchQuerySet().within('location', downtown_bottom_left, downtown_top_right)

    # Can be chained with other Haystack calls.
    sqs = SearchQuerySet().auto_query('coffee').within('location', downtown_bottom_left, downtown_top_right).order_by('-popularity')

.. note::

    In GeoDjango, assuming the ``Shop`` model had been properly geo-ified, this
    would have been implemented as::

        from shops.models import Shop
        Shop.objects.filter(location__within=(downtown_bottom_left, downtown_top_right))

    Haystack's form differs because it yielded a cleaner implementation, was
    no more typing than the GeoDjango version & tried to maintain the same
    terminology/similar signature.


``dwithin``
-----------

.. method:: SearchQuerySet.dwithin(self, field, point, distance)

``dwithin`` is a radius-based search. A radius-based search is a circular area
within which to search. It's composed of a center point & a radius (in
kilometers, though Haystack will use the ``D`` object's conversion utilities to
get it there). It is slower than``within`` but very exact & can involve fewer
calculations on your part.

Examples::

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point, D

    ninth_and_mass = Point(-95.23592948913574, 38.96753407043678)
    # Within a two miles.
    max_dist = D(mi=2)

    # 'location' is the fieldname from our ``SearchIndex``...

    # Do the radius query.
    sqs = SearchQuerySet().dwithin('location', ninth_and_mass, max_dist)

    # Can be chained with other Haystack calls.
    sqs = SearchQuerySet().auto_query('coffee').dwithin('location', ninth_and_mass, max_dist).order_by('-popularity')

.. note::

    In GeoDjango, assuming the ``Shop`` model had been properly geo-ified, this
    would have been implemented as::

        from shops.models import Shop
        Shop.objects.filter(location__dwithin=(ninth_and_mass, D(mi=2)))

    Haystack's form differs because it yielded a cleaner implementation, was
    no more typing than the GeoDjango version & tried to maintain the same
    terminology/similar signature.


``distance``
------------

.. method:: SearchQuerySet.distance(self, field, point)

By default, search results will come back without distance information attached
to them. In the concept of a bounding box, it would be ambiguous what the
distances would be calculated against. And it is more calculation that may not
be necessary.

So like GeoDjango, Haystack exposes a method to signify that you want to
include these calculated distances on results.

Examples::

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point, D

    ninth_and_mass = Point(-95.23592948913574, 38.96753407043678)

    # On a bounding box...
    downtown_bottom_left = Point(-95.23947, 38.9637903)
    downtown_top_right = Point(-95.23362278938293, 38.973081081164715)

    sqs = SearchQuerySet().within('location', downtown_bottom_left, downtown_top_right).distance('location', ninth_and_mass)

    # ...Or on a radius query.
    sqs = SearchQuerySet().dwithin('location', ninth_and_mass, D(mi=2)).distance('location', ninth_and_mass)

You can even apply a different field, for instance if you calculate results of
key, well-cached hotspots in town but want distances from the user's current
position::

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point, D

    ninth_and_mass = Point(-95.23592948913574, 38.96753407043678)
    user_loc = Point(-95.23455619812012, 38.97240128290697)

    sqs = SearchQuerySet().dwithin('location', ninth_and_mass, D(mi=2)).distance('location', user_loc)

.. note::

    The astute will notice this is Haystack's biggest departure from GeoDjango.
    In GeoDjango, this would have been implemented as::

        from shops.models import Shop
        Shop.objects.filter(location__dwithin=(ninth_and_mass, D(mi=2))).distance(user_loc)

    Note that, by default, the GeoDjango form leaves *out* the field to be
    calculating against (though it's possible to override it & specify the
    field).

    Haystack's form differs because the same assumptions are difficult to make.
    GeoDjango deals with a single model at a time, where Haystack deals with
    a broad mix of models. Additionally, accessing ``Model`` information is a
    couple hops away, so Haystack favors the explicit (if slightly more typing)
    approach.


Ordering
========

Because you're dealing with search, even with geospatial queries, results still
come back in **RELEVANCE** order. If you want to offer the user ordering
results by distance, there's a simple way to enable this ordering.

Using the standard Haystack ``order_by`` method, if you specify ``distance`` or
``-distance`` **ONLY**, you'll get geographic ordering. Additionally, you must
have a call to ``.distance()`` somewhere in the chain, otherwise there is no
distance information on the results & nothing to sort by.

Examples::

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point, D

    ninth_and_mass = Point(-95.23592948913574, 38.96753407043678)
    downtown_bottom_left = Point(-95.23947, 38.9637903)
    downtown_top_right = Point(-95.23362278938293, 38.973081081164715)

    # Non-geo ordering.
    sqs = SearchQuerySet().within('location', downtown_bottom_left, downtown_top_right).order_by('title')
    sqs = SearchQuerySet().within('location', downtown_bottom_left, downtown_top_right).distance('location', ninth_and_mass).order_by('-created')

    # Geo ordering, closest to farthest.
    sqs = SearchQuerySet().within('location', downtown_bottom_left, downtown_top_right).distance('location', ninth_and_mass).order_by('distance')
    # Geo ordering, farthest to closest.
    sqs = SearchQuerySet().dwithin('location', ninth_and_mass, D(mi=2)).distance('location', ninth_and_mass).order_by('-distance')

.. note::

    This call is identical to the GeoDjango usage.

.. warning::

    You can not specify both a distance & lexicographic ordering. If you specify
    more than just ``distance`` or ``-distance``, Haystack assumes ``distance``
    is a field in the index & tries to sort on it. Example::

        # May blow up!
        sqs = SearchQuerySet().dwithin('location', ninth_and_mass, D(mi=2)).distance('location', ninth_and_mass).order_by('distance', 'title')

    This is a limitation in the engine's implementation.

    If you actually **have** a field called ``distance`` (& aren't using
    calculated distance information), Haystack will do the right thing in
    these circumstances.


Caveats
=======

In all cases, you may call the ``within/dwithin/distance`` methods as many times
as you like. However, the **LAST** call is the information that will be used.
No combination logic is available, as this is largely a backend limitation.

Combining calls to both ``within`` & ``dwithin`` may yield unexpected or broken
results. They don't overlap when performing queries, so it may be possible to
construct queries that work. Your Mileage May Vary.
