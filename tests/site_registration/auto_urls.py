from django.conf.urls.defaults import *

import haystack
haystack.autodiscover()

urlpatterns = patterns('',
    (r'^search/', include('haystack.urls')),
)
