# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from django.db import models


class Checkin(models.Model):
    username = models.CharField(max_length=255)
    # We're going to do some non-GeoDjango action, since the setup is
    # complex enough. You could just as easily do:
    #
    #   location = models.PointField()
    #
    # ...and your ``search_indexes.py`` could be less complex.
    latitude = models.FloatField()
    longitude = models.FloatField()
    comment = models.CharField(max_length=140, blank=True, default='', help_text='Say something pithy.')
    created = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ['-created']

    # Again, with GeoDjango, this would be unnecessary.
    def get_location(self):
        # Nothing special about this Point, but ensure that's we don't have to worry
        # about import paths.
        from haystack.utils.geo import Point
        pnt = Point(self.longitude, self.latitude)
        return pnt


class CheckinMulti(models.Model):
    username = models.CharField(max_length=255)
    latitude1 = models.FloatField()
    longitude1 = models.FloatField()
    latitude2 = models.FloatField()
    longitude2 = models.FloatField()
    comment = models.CharField(max_length=140, blank=True, default='', help_text='Say something pithy.')
    created = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ['-created']

    def get_multi_locations(self):
        from haystack.utils.geo import Point
        pnt1 = Point(self.longitude1, self.latitude1)
        pnt2 = Point(self.longitude2, self.latitude2)
        return [pnt1, pnt2]
