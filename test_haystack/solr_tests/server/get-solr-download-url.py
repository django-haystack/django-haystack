#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain
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

download_url = urljoin('https://archive.apache.org/dist/', dist_path)
mirror_response = requests.get("https://www.apache.org/dyn/mirrors/mirrors.cgi/%s?asjson=1" % dist_path)

if not mirror_response.ok:
    print('Apache mirror request returned HTTP %d' % mirror_response.status_code, file=sys.stderr)
    sys.exit(1)

mirror_data = mirror_response.json()

# Since the Apache mirrors are often unreliable and releases may disappear without notice we'll
# try the preferred mirror, all of the alternates and backups, and fall back to the main Apache
# archive server:
for base_url in chain((mirror_data['preferred'], ), mirror_data['http'], mirror_data['backup'],
                      ('https://archive.apache.org/dist/', )):
    test_url = urljoin(base_url, mirror_data['path_info'])

    # The Apache mirror script's response format has recently changed to exclude the actual file paths:
    if not test_url.endswith(tarball):
        test_url = urljoin(test_url, dist_path)

    if requests.head(test_url, allow_redirects=True).status_code == 200:
        download_url = test_url
        break
else:
    print('None of the Apache mirrors have %s' % dist_path, file=sys.stderr)
    sys.exit(1)

print(download_url)
