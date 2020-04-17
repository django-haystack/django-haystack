# A couple models for Haystack to test with.
import datetime
import uuid

from django.db import models


class MockTag(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class MockModel(models.Model):
    author = models.CharField(max_length=255)
    foo = models.CharField(max_length=255, blank=True)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    tag = models.ForeignKey(MockTag, models.CASCADE)

    def __str__(self):
        return self.author

    def hello(self):
        return "World!"


class UUIDMockModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    characteristics = models.TextField()

    def __str__(self):
        return str(self.id)


class AnotherMockModel(models.Model):
    author = models.CharField(max_length=255)
    pub_date = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return self.author


class AThirdMockModel(AnotherMockModel):
    average_delay = models.FloatField(default=0.0)
    view_count = models.PositiveIntegerField(default=0)


class CharPKMockModel(models.Model):
    key = models.CharField(primary_key=True, max_length=10)


class AFourthMockModel(models.Model):
    author = models.CharField(max_length=255)
    editor = models.CharField(max_length=255)
    pub_date = models.DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return self.author


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)

    def complete_set(self):
        return super().get_queryset()


class AFifthMockModel(models.Model):
    author = models.CharField(max_length=255)
    deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    def __str__(self):
        return self.author


class ASixthMockModel(models.Model):
    name = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()

    def __str__(self):
        return self.name


class ScoreMockModel(models.Model):
    score = models.CharField(max_length=10)

    def __str__(self):
        return self.score


class ManyToManyLeftSideModel(models.Model):
    related_models = models.ManyToManyField("ManyToManyRightSideModel")


class ManyToManyRightSideModel(models.Model):
    name = models.CharField(max_length=32, default="Default name")

    def __str__(self):
        return self.name


class OneToManyLeftSideModel(models.Model):
    pass


class OneToManyRightSideModel(models.Model):
    left_side = models.ForeignKey(
        OneToManyLeftSideModel, models.CASCADE, related_name="right_side"
    )
