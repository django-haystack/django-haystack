# Find and load the search backend.  This code shold look pretty familier if
# you've examined django.db.backends recently...

import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__all__ = ['backend']

if not hasattr(settings, "SEARCH_ENGINE"):
    raise ImproperlyConfigured("You must define the SEARCH_ENGINE setting before using the search framework.")

try:
    # Most of the time, the search backend will be one of the  
    # backends that ships with django-search, so look there first.
    backend = __import__('djangosearch.backends.%s' % settings.SEARCH_ENGINE, {}, {}, [''])
except ImportError, e:
    # If the import failed, we might be looking for a search backend 
    # distributed external to django-search. So we'll try that next.
    try:
        backend = __import__(settings.SEARCH_ENGINE, {}, {}, [''])
    except ImportError, e_user:
        # The database backend wasn't found. Display a helpful error message
        # listing all possible (built-in) database backends.
        backend_dir = os.path.join(__path__[0], 'backends')
        available_backends = [
            os.path.splitext(f)[0] for f in os.listdir(__path__[0])
            if f != "base.py"
            and not f.startswith('_') 
            and not f.startswith('.') 
            and not f.endswith('.pyc')
        ]
        available_backends.sort()
        if settings.SEARCH_ENGINE not in available_backends:
            raise ImproperlyConfigured, "%r isn't an available search backend. Available options are: %s" % \
                (settings.SEARCH_ENGINE, ", ".join(map(repr, available_backends)))
        else:
            raise # If there's some other error, this must be an error in Django itself.
