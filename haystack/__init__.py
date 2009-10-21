import inspect
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from haystack.sites import site


__author__ = 'Daniel Lindsley'
__version__ = (1, 0, 0, 'beta')
__all__ = ['backend']


if not hasattr(settings, "HAYSTACK_SITECONF"):
    raise ImproperlyConfigured("You must define the HAYSTACK_SITECONF setting before using the search framework.")
if not hasattr(settings, "HAYSTACK_SEARCH_ENGINE"):
    raise ImproperlyConfigured("You must define the HAYSTACK_SEARCH_ENGINE setting before using the search framework.")


# Load the search backend.
def load_backend(backend_name=None):
    if not backend_name:
        backend_name = settings.HAYSTACK_SEARCH_ENGINE
    
    try:
        # Most of the time, the search backend will be one of the  
        # backends that ships with haystack, so look there first.
        return __import__('haystack.backends.%s_backend' % backend_name, {}, {}, [''])
    except ImportError, e:
        # If the import failed, we might be looking for a search backend 
        # distributed external to haystack. So we'll try that next.
        try:
            return __import__('%s_backend' % backend_name, {}, {}, [''])
        except ImportError, e_user:
            # The search backend wasn't found. Display a helpful error message
            # listing all possible (built-in) database backends.
            backend_dir = os.path.join(__path__[0], 'backends')
            available_backends = [
                os.path.splitext(f)[0].split("_backend")[0] for f in os.listdir(backend_dir)
                if f != "base.py"
                and not f.startswith('_') 
                and not f.startswith('.') 
                and not f.endswith('.pyc')
            ]
            available_backends.sort()
            if backend_name not in available_backends:
                raise ImproperlyConfigured, "%r isn't an available search backend. Available options are: %s" % \
                    (backend_name, ", ".join(map(repr, available_backends)))
            else:
                raise # If there's some other error, this must be an error in Django itself.


backend = load_backend(settings.HAYSTACK_SEARCH_ENGINE)


def autodiscover():
    """
    Automatically build the site index.
    
    Again, almost exactly as django.contrib.admin does things, for consistency.
    """
    import imp
    from django.conf import settings
    
    for app in settings.INSTALLED_APPS:
        # For each app, we need to look for an search_indexes.py inside that app's
        # package. We can't use os.path here -- recall that modules may be
        # imported different ways (think zip files) -- so we need to get
        # the app's __path__ and look for search_indexes.py on that path.
        
        # Step 1: find out the app's __path__ Import errors here will (and
        # should) bubble up, but a missing __path__ (which is legal, but weird)
        # fails silently -- apps that do weird things with __path__ might
        # need to roll their own index registration.
        try:
            app_path = __import__(app, {}, {}, [app.split('.')[-1]]).__path__
        except AttributeError:
            continue
        
        # Step 2: use imp.find_module to find the app's search_indexes.py. For some
        # reason imp.find_module raises ImportError if the app can't be found
        # but doesn't actually try to import the module. So skip this app if
        # its search_indexes.py doesn't exist
        try:
            imp.find_module('search_indexes', app_path)
        except ImportError:
            continue
        
        # Step 3: import the app's search_index file. If this has errors we want them
        # to bubble up.
        __import__("%s.search_indexes" % app)

# Make sure the site gets loaded.
def handle_registrations(*args, **kwargs):
    """
    Ensures that any configuration of the SearchSite(s) are handled when
    importing Haystack.
    
    This makes it possible for scripts/management commands that affect models
    but know nothing of Haystack to keep the index up to date.
    """
    # DRL_TODO: Some day, Django may feature a way to iterate over models without
    #           loading everything (partial load). When that comes, we'll need a
    #           version check here.
    
    # This is a little dirty but we need to run the code that follows only
    # once, no matter how many times the main Haystack module is imported.
    # We'll look through the stack to see if we appear anywhere and simply
    # return if we do, allowing the original call to finish.
    stack = inspect.stack()
    
    for stack_info in stack[1:]:
        if 'handle_registrations' in stack_info[3]:
            return
    
    from django.db import models
    
    # Force the AppCache to populate. We need it loaded to be able to
    # register using the generated Model classes, which are only fully there
    # after the cache is loaded.
    models.loading.cache.get_apps()
    
    # Pull in the config file, causing any SearchSite initialization code to
    # execute.
    search_sites_conf = __import__(settings.HAYSTACK_SITECONF)


handle_registrations()
