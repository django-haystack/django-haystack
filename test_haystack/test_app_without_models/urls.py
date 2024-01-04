from django.urls import path

from .views import simple_view

urlpatterns = [path("simple-view", simple_view, name="simple-view")]
