import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from haystack.indexes import SearchIndex
from haystack.sites import SearchIndex, site


__author__ = 'Daniel Lindsley'
__version__ = (2, 0, 0, 'beta')
__all__ = ['backend']


# Load the search backend.
if not hasattr(settings, "SEARCH_ENGINE"):
    raise ImproperlyConfigured("You must define the SEARCH_ENGINE setting before using the search framework.")

try:
    # Most of the time, the search backend will be one of the  
    # backends that ships with haystack, so look there first.
    backend = __import__('haystack.backends.%s' % settings.SEARCH_ENGINE, {}, {}, [''])
except ImportError, e:
    # If the import failed, we might be looking for a search backend 
    # distributed external to haystack. So we'll try that next.
    try:
        backend = __import__(settings.SEARCH_ENGINE, {}, {}, [''])
    except ImportError, e_user:
        # The database backend wasn't found. Display a helpful error message
        # listing all possible (built-in) database backends.
        backend_dir = os.path.join(__path__[0], 'backends')
        available_backends = [
            os.path.splitext(f)[0] for f in os.listdir(backend_dir)
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


def autodiscover():
    """
    Automatically build the site index.
    
    Again, almost exactly as django.contrib.admin does things, for consistency.
    """
    import imp
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        # For each app, we need to look for an indexes.py inside that app's
        # package. We can't use os.path here -- recall that modules may be
        # imported different ways (think zip files) -- so we need to get
        # the app's __path__ and look for indexes.py on that path.

        # Step 1: find out the app's __path__ Import errors here will (and
        # should) bubble up, but a missing __path__ (which is legal, but weird)
        # fails silently -- apps that do weird things with __path__ might
        # need to roll their own index registration.
        try:
            app_path = __import__(app, {}, {}, [app.split('.')[-1]]).__path__
        except AttributeError:
            continue

        # Step 2: use imp.find_module to find the app's indexes.py. For some
        # reason imp.find_module raises ImportError if the app can't be found
        # but doesn't actually try to import the module. So skip this app if
        # its indexes.py doesn't exist
        try:
            imp.find_module('indexes', app_path)
        except ImportError:
            continue

        # Step 3: import the app's index file. If this has errors we want them
        # to bubble up.
        __import__("%s.indexes" % app)
