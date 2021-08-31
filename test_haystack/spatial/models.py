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
    comment = models.CharField(
        max_length=140, blank=True, default="", help_text="Say something pithy."
    )
    created = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        ordering = ["-created"]

    # Again, with GeoDjango, this would be unnecessary.
    def get_location(self):
        # Nothing special about this Point, but ensure that's we don't have to worry
        # about import paths.
        from django.contrib.gis.geos import Point

        pnt = Point(self.longitude, self.latitude)
        return pnt
