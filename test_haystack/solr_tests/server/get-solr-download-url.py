#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

import sys

import requests

# Try to import urljoin from the Python 3 reorganized stdlib first:
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


if len(sys.argv) != 2:
    print('Usage: %s SOLR_VERSION' % sys.argv[0], file=sys.stderr)
    sys.exit(1)

solr_version = sys.argv[1]
tarball = 'solr-{0}.tgz'.format(solr_version)
dist_path = 'lucene/solr/{0}/{1}'.format(solr_version, tarball)

download_url = urljoin('http://archive.apache.org/dist/', dist_path)
mirror_response = requests.get("http://www.apache.org/dyn/mirrors/mirrors.cgi/%s?asjson=1" % dist_path)

if mirror_response.ok:
    mirror_data = mirror_response.json()
    download_url = urljoin(mirror_data['preferred'], mirror_data['path_info'])

print(download_url)
