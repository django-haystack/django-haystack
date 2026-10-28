# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ImproperlyConfigured

from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, EmptyResults, log_query
from haystack.backends.solr_backend import SolrSearchBackend, SolrSearchQuery
from haystack.exceptions import MissingDependency
from haystack.utils import log as logging

try:
    from pysolr import ZooKeeper, SolrCloud
except ImportError:
    raise MissingDependency("The 'solrcloud' backend requires the installation of 'pysolr'. Please refer to the documentation.")

class SolrCloudSearchBackend(SolrSearchBackend):
    def __init__(self, connection_alias, **connection_options):
        super(SolrSearchBackend, self).__init__(connection_alias, **connection_options)

        if 'URL' not in connection_options:
            raise ImproperlyConfigured("You must specify a 'URL' in your settings for connection '%s'." % connection_alias)

        if 'COLLECTION' not in connection_options:
            raise ImproperlyConfigured("You must specify a 'collection' in your settings for connection '%s'." % connection_alias)


        self.collate = connection_options.get('COLLATE_SPELLING', True)

        zookeeper = ZooKeeper(connection_options['URL'])
        self.conn = SolrCloud(zookeeper, connection_options['COLLECTION'], timeout=self.timeout,
                         **connection_options.get('KWARGS', {}))
        self.log = logging.getLogger('haystack')


class SolrCloudEngine(BaseEngine):
    backend = SolrCloudSearchBackend
    query = SolrSearchQuery