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
    mkdir solr
    tar -C solr -xf solr-X.Y.0.tgz --strip-components=1
    cd solr
    ./bin/solr start                                    # start solr
    ./bin/solr create -c tester -n basic_config         # create core named 'tester'

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

You'll also need to install the ``pysolr`` client library from PyPI::

    $ pip install pysolr

More Like This
--------------

On Solr 6.X+ "More Like This" functionality is enabled by default. To enable 
the "More Like This" functionality on earlier versions of Solr, you'll need
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
    
      <str name="queryAnalyzerFieldType">text_general</str>
      <lst name="spellchecker">
        <str name="name">default</str>
        <str name="field">text</str>
        <str name="classname">solr.DirectSolrSpellChecker</str>
        <str name="distanceMeasure">internal</str>
        <float name="accuracy">0.5</float>
        <int name="maxEdits">2</int>
        <int name="minPrefix">1</int>
        <int name="maxInspections">5</int>
        <int name="minQueryLength">4</int>
        <float name="maxQueryFrequency">0.01</float>
      </lst>
    </searchComponent>

Then change your default handler from::

    <requestHandler name="/select" class="solr.SearchHandler">
      <lst name="defaults">
        <str name="echoParams">explicit</str>
        <int name="rows">10</int>
      </lst>
    </requestHandler>
    
... to ...::

    <requestHandler name="/select" class="solr.SearchHandler">
      <lst name="defaults">
        <str name="echoParams">explicit</str>
        <int name="rows">10</int>
      
        <str name="spellcheck.dictionary">default</str>
        <str name="spellcheck">on</str>
        <str name="spellcheck.extendedResults">true</str>
        <str name="spellcheck.count">10</str>
        <str name="spellcheck.alternativeTermCount">5</str>
        <str name="spellcheck.maxResultsForSuggest">5</str>
        <str name="spellcheck.collate">true</str>
        <str name="spellcheck.collateExtendedResults">true</str>
        <str name="spellcheck.maxCollationTries">10</str>
        <str name="spellcheck.maxCollations">5</str>
       </lst>
       <arr name="last-components">
         <str>spellcheck</str>
       </arr>
    </requestHandler>

Be warned that the ``<str name="field">suggestions</str>`` portion will be specific to
your ``SearchIndex`` classes (in this case, assuming the main field is called
``text``).


Elasticsearch
=============

Elasticsearch is similar to Solr — another Java application using Lucene — but
focused on ease of deployment and clustering. See
https://www.elastic.co/products/elasticsearch for more information.

Haystack currently supports Elasticsearch 1.x, 2.x, and 5.x.

Follow the instructions on https://www.elastic.co/downloads/elasticsearch to
download and install Elasticsearch and configure it for your environment.

You'll also need to install the Elasticsearch binding: elasticsearch_ for the
appropriate backend version — for example::

    $ pip install "elasticsearch>=5,<6"

.. _elasticsearch: https://pypi.python.org/pypi/elasticsearch/


Whoosh
======

Official Download Location: https://github.com/whoosh-community/whoosh

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
