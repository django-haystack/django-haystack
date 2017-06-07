.. _ref-installing-search-engines:

=========================
Installing Search Engines
=========================

Solr
====

Official Download Location: http://www.apache.org/dyn/closer.cgi/lucene/solr/

Solr is Java but comes in a pre-packaged form that requires very little other
than the JRE and Jetty. It's very performant and has an advanced featureset.
Haystack suggests using Solr 6.x, though it's possible to get it working on
Solr 4.x+ with a little effort. Installation is relatively simple:

For Solr 6.X::

    curl -LO https://archive.apache.org/dist/lucene/solr/x.Y.0/solr-X.Y.0.tgz
    tar -C solr -xf solr-X.Y.0.tgz --strip-components=1
    cd solr
    ./bin/solr create -c tester -n basic_config

By default this will create a core with a managed schema.  This setup is dynamic
but not useful for haystack, and we'll need to configure solr to use a static
(classic) schema.  Haystack can generate a viable schema.xml and solrconfig.xml
for you from your application and reload the core for you (once Haystack is
installed and setup).  To do this run:
``./manage.py build_solr_schema --configure-directory=<CoreConfigDif>
--reload-core``. In this example CoreConfigDir is something like
``../solr-6.5.0/server/solr/tester/conf``, and ``--reload-core``
is what triggers reloading of the core.  Please refer to ``build_solr_schema``
in the :doc:`management-commands` for required configuration.

For Solr 4.X::

    curl -LO https://archive.apache.org/dist/lucene/solr/4.10.2/solr-4.10.2.tgz
    tar xvzf solr-4.10.2.tgz
    cd solr-4.10.2
    cd example
    java -jar start.jar

You’ll need to revise your schema. You can generate this from your application
(once Haystack is installed and setup) by running
``./manage.py build_solr_schema``. Take the output from that command and place
it in ``solr-4.10.2/example/solr/collection1/conf/schema.xml``. Then restart
Solr.

.. warning::
    Please note; the template filename, the file YOU supply under
    TEMPLATE_DIR/search_configuration has changed to schema.xml from solr.xml.
    The previous template name solr.xml was a legacy holdover from older
    versions of solr.

You'll also need a Solr binding, ``pysolr``. The official ``pysolr`` package,
distributed via PyPI, is the best version to use (2.1.0+). Place ``pysolr.py``
somewhere on your ``PYTHONPATH``.

.. note::

    ``pysolr`` has its own dependencies that aren't covered by Haystack. See
    https://pypi.python.org/pypi/pysolr for the latest documentation.  Simplest
    approach is to install using ``pip install pysolr``

More Like This
--------------

To enable the "More Like This" functionality in Haystack, you'll need
to enable the ``MoreLikeThisHandler``. Add the following line to your
``solrconfig.xml`` file within the ``config`` tag::

    <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />

Spelling Suggestions
--------------------

To enable the spelling suggestion functionality in Haystack, you'll need to
enable the ``SpellCheckComponent``.

The first thing to do is create a special field on your ``SearchIndex`` class
that mirrors the ``text`` field, but uses ``FacetCharField``. This disables
the post-processing that Solr does, which can mess up your suggestions.
Something like the following is suggested::

    class MySearchIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        # ... normal fields then...
        suggestions = indexes.FacetCharField()

        def prepare(self, obj):
            prepared_data = super(MySearchIndex, self).prepare(obj)
            prepared_data['suggestions'] = prepared_data['text']
            return prepared_data

Then, you enable it in Solr by adding the following line to your
``solrconfig.xml`` file within the ``config`` tag::

    <searchComponent name="spellcheck" class="solr.SpellCheckComponent">

        <str name="queryAnalyzerFieldType">textSpell</str>

        <lst name="spellchecker">
          <str name="name">default</str>
          <str name="field">suggestions</str>
          <str name="spellcheckIndexDir">./spellchecker1</str>
          <str name="buildOnCommit">true</str>
        </lst>
    </searchComponent>

Then change your default handler from::

    <requestHandler name="standard" class="solr.StandardRequestHandler" default="true" />

... to ...::

    <requestHandler name="standard" class="solr.StandardRequestHandler" default="true">
        <arr name="last-components">
            <str>spellcheck</str>
        </arr>
    </requestHandler>

Be warned that the ``<str name="field">suggestions</str>`` portion will be specific to
your ``SearchIndex`` classes (in this case, assuming the main field is called
``text``).


Elasticsearch
=============

Official Download Location: http://www.elasticsearch.org/download/

Elasticsearch is Java but comes in a pre-packaged form that requires very
little other than the JRE. It's also very performant, scales easily and has
an advanced featureset. Haystack currently only supports Elasticsearch 1.x and 2.x.
Elasticsearch 5.x is not supported yet, if you would like to help, please see
`#1383 <https://github.com/django-haystack/django-haystack/issues/1383>`_.

Installation is best done using a package manager::

    # On Mac OS X...
    brew install elasticsearch

    # On Ubuntu...
    apt-get install elasticsearch

    # Then start via:
    elasticsearch -f -D es.config=<path to YAML config>

    # Example:
    elasticsearch -f -D es.config=/usr/local/Cellar/elasticsearch/0.90.0/config/elasticsearch.yml

You may have to alter the configuration to run on ``localhost`` when developing
locally. Modifications should be done in a YAML file, the stock one being
``config/elasticsearch.yml``::

    # Unicast Discovery (disable multicast)
    discovery.zen.ping.multicast.enabled: false
    discovery.zen.ping.unicast.hosts: ["127.0.0.1"]

    # Name your cluster here to whatever.
    # My machine is called "Venus", so...
    cluster:
      name: venus

    network:
      host: 127.0.0.1

    path:
      logs: /usr/local/var/log
      data: /usr/local/var/data

You'll also need an Elasticsearch binding: elasticsearch_ (**NOT**
``pyes``). Place ``elasticsearch`` somewhere on your ``PYTHONPATH``
(usually ``python setup.py install`` or ``pip install elasticsearch``).

.. _elasticsearch: http://pypi.python.org/pypi/elasticsearch/

.. note::

    ``elasticsearch`` has its own dependencies that aren't covered by
    Haystack. You'll also need ``urllib3``.


Whoosh
======

Official Download Location: http://bitbucket.org/mchaput/whoosh/

Whoosh is pure Python, so it's a great option for getting started quickly and
for development, though it does work for small scale live deployments. The
current recommended version is 1.3.1+. You can install via PyPI_ using
``sudo easy_install whoosh`` or ``sudo pip install whoosh``.

Note that, while capable otherwise, the Whoosh backend does not currently
support "More Like This" or faceting. Support for these features has recently
been added to Whoosh itself & may be present in a future release.

.. _PyPI: http://pypi.python.org/pypi/Whoosh/


Xapian
======

Official Download Location: http://xapian.org/download

Xapian is written in C++ so it requires compilation (unless your OS has a
package for it). Installation looks like::

    curl -O http://oligarchy.co.uk/xapian/1.2.18/xapian-core-1.2.18.tar.xz
    curl -O http://oligarchy.co.uk/xapian/1.2.18/xapian-bindings-1.2.18.tar.xz

    unxz xapian-core-1.2.18.tar.xz
    unxz xapian-bindings-1.2.18.tar.xz

    tar xvf xapian-core-1.2.18.tar
    tar xvf xapian-bindings-1.2.18.tar

    cd xapian-core-1.2.18
    ./configure
    make
    sudo make install

    cd ..
    cd xapian-bindings-1.2.18
    ./configure
    make
    sudo make install

Xapian is a third-party supported backend. It is not included in Haystack
proper due to licensing. To use it, you need both Haystack itself as well as
``xapian-haystack``. You can download the source from
http://github.com/notanumber/xapian-haystack/tree/master. Installation
instructions can be found on that page as well. The backend, written
by David Sauve (notanumber), fully implements the `SearchQuerySet` API and is
an excellent alternative to Solr.
