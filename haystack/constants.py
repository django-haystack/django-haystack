from django.conf import settings

# Reserved field names
ID = getattr(settings, 'HAYSTACK_ID_FIELD', 'id')
DJANGO_CT = getattr(settings, 'HAYSTACK_DJANGO_CT_FIELD', 'django_ct')
DJANGO_ID = getattr(settings, 'HAYSTACK_DJANGO_ID_FIELD', 'django_id')

# Default operator. Valid options are AND/OR.
DEFAULT_OPERATOR = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', 'AND')

# Valid expression extensions.
VALID_FILTERS = set(['exact', 'gt', 'gte', 'lt', 'lte', 'in', 'startswith', 'range'])
FILTER_SEPARATOR = '__'

# The maximum number of items to display in a SearchQuerySet.__repr__
REPR_OUTPUT_SIZE = 20

# Number of SearchResults to load at a time.
ITERATOR_LOAD_PER_QUERY = getattr(settings, 'HAYSTACK_ITERATOR_LOAD_PER_QUERY', 10)
