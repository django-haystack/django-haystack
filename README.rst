For specific instructions on this fork, scroll down.

========
Haystack
========

:author: Daniel Lindsley
:date: 2011/09/18

Haystack provides modular search for Django. It features a unified, familiar
API that allows you to plug in different search backends (such as Solr_,
Whoosh_, Xapian_, etc.) without having to modify your code.

.. _Solr: http://lucene.apache.org/solr/
.. _Whoosh: http://whoosh.ca/
.. _Xapian: http://xapian.org/

Haystack is BSD licensed, plays nicely with third-party app without needing to
modify the source and supports advanced features like faceting, More Like This,
highlighting and spelling suggestions.

You can find more information at http://haystacksearch.org/.


Getting Help
============

There is a mailing list (http://groups.google.com/group/django-haystack/)
available for general discussion and an IRC channel (#haystack on
irc.freenode.net).


Documentation
=============

* Development version: http://docs.haystacksearch.org/dev/
* v1.1: http://docs.haystacksearch.org/1.1/
* v1.0: http://docs.haystacksearch.org/1.0/


Requirements
============

Haystack has a relatively easily-met set of requirements.

* Python 2.5+
* Django 1.2+

Additionally, each backend has its own requirements. You should refer to
http://docs.haystacksearch.org/dev/installing_search_engines.html for more
details.

========
SPECIFIC TO THIS FORK
========

:author: __jnaut__

Additional Requirements
============
Minimum Solr version is 3.2 

Note: Even though native spatial search was introduced in Solr 3.1 but it turned out to be too buggy and it is highly advised that min. version 3.2 be used.

Model
============
The model should have two attributes named - latitude and longitude.

e.g.::

    class Restaurant(models.Model):
        name = models.CharField(max_length=255)
        latitude = models.FloatField(blank=True)
        longitude = models.FloatField(blank=True)

(see example at example_project_with_spatial_solr/spatial_app/models.py)

SearchIndex
============
The searchindex will NOT have latitude or longitude fields. Instead, it will only have one field of type LocationField.

e.g.::

    class RestaurantIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        name = indexes.CharField(model_attr='name')
        geocode = indexes.LocationField()

(see example at example_project_with_spatial_solr/spatial_app/search_indexes.py)

Search
============
The search method for spatial search is: ``haystack.query.SearchQuerySet().spatial(**kwargs)`` .

It works just like filter method and returns a SearchQuerySet instance.

Syntax::

    spatial(lat=<latitude-float>, lng=<longitude-float>, sfield=<field_of_type_location_in_SearchIndex-string>, 
            radius=<radius_in_kms-float>, [sort_by_distance=<bool>, [sort_order='asc/desc-string']])

e.g.::

    sqs = SearchQuerySet()
    sqs = sqs.spatial(lat=-34.7777, lng=138.534556, sfield='geocode', radius=10.8)

(see example at example_project_with_spatial_solr/spatial_app/views.py)