# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings

DEFAULT_ALIAS = 'default'

# Reserved field names
ID = getattr(settings, 'HAYSTACK_ID_FIELD', 'id')
DJANGO_CT = getattr(settings, 'HAYSTACK_DJANGO_CT_FIELD', 'django_ct')
DJANGO_ID = getattr(settings, 'HAYSTACK_DJANGO_ID_FIELD', 'django_id')
DOCUMENT_FIELD = getattr(settings, 'HAYSTACK_DOCUMENT_FIELD', 'text')

# Default operator. Valid options are AND/OR.
DEFAULT_OPERATOR = getattr(settings, 'HAYSTACK_DEFAULT_OPERATOR', 'AND')

# Default values on elasticsearch
FUZZY_MIN_SIM = getattr(settings, 'HAYSTACK_FUZZY_MIN_SIM', 0.5)
FUZZY_MAX_EXPANSIONS = getattr(settings, 'HAYSTACK_FUZZY_MAX_EXPANSIONS', 50)

# Valid expression extensions.
VALID_FILTERS = set(['contains', 'exact', 'gt', 'gte', 'lt', 'lte', 'in', 'startswith', 'range', 'endswith', 'content', 'fuzzy'])

FILTER_SEPARATOR = '__'

# The maximum number of items to display in a SearchQuerySet.__repr__
REPR_OUTPUT_SIZE = 20

# Number of SearchResults to load at a time.
ITERATOR_LOAD_PER_QUERY = getattr(settings, 'HAYSTACK_ITERATOR_LOAD_PER_QUERY', 10)

# A marker class in the hierarchy to indicate that it handles search data.
class Indexable(object):
    haystack_use_for_indexing = True

# For the geo bits, since that's what Solr & Elasticsearch seem to silently
# assume...
WGS_84_SRID = 4326
