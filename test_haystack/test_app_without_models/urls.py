# encoding: utf-8
from django.conf.urls import url

from .views import simple_view

urlpatterns = [url(r"^simple-view$", simple_view, name="simple-view")]
