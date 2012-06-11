from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from haystack.constants import DEFAULT_ALIAS


# Help people clean up from 1.X.
if hasattr(settings, 'HAYSTACK_SITECONF'):
    raise ImproperlyConfigured('The HAYSTACK_SITECONF setting is no longer used & can be removed.')
if hasattr(settings, 'HAYSTACK_SEARCH_ENGINE'):
    raise ImproperlyConfigured('The HAYSTACK_SEARCH_ENGINE setting has been replaced with HAYSTACK_CONNECTIONS.')
if hasattr(settings, 'HAYSTACK_ENABLE_REGISTRATIONS'):
    raise ImproperlyConfigured('The HAYSTACK_ENABLE_REGISTRATIONS setting is no longer used & can be removed.')
if hasattr(settings, 'HAYSTACK_INCLUDE_SPELLING'):
    raise ImproperlyConfigured('The HAYSTACK_INCLUDE_SPELLING setting is now a per-backend setting & belongs in HAYSTACK_CONNECTIONS.')


# Check the 2.X+ bits.
if not hasattr(settings, 'HAYSTACK_CONNECTIONS'):
    raise ImproperlyConfigured('The HAYSTACK_CONNECTIONS setting is required.')
if DEFAULT_ALIAS not in settings.HAYSTACK_CONNECTIONS:
    raise ImproperlyConfigured("The default alias '%s' must be included in the HAYSTACK_CONNECTIONS setting." % DEFAULT_ALIAS)
