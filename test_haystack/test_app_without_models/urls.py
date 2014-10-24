from django.conf.urls import patterns, url

from .views import simple_view

urlpatterns = patterns('',
                       url(r'^simple-view$', simple_view, name='simple-view'))
