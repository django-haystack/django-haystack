=========================
Installing Search Engines
=========================

Solr
====

Official Download Location: http://www.apache.org/dyn/closer.cgi/lucene/solr/

Solr is Java but comes in a pre=packaged form that requires very little other
than the JRE and Jetty. It's very performant and has an advanced featureset.
Haystack requires Solr 1.3+. Installation is relatively simple::

    curl -O http://apache.mirrors.tds.net/lucene/solr/1.3.0/apache-solr-1.3.0.tgz
    tar xvzf apache-solr-1.3.0.tgz
    cd apache-solr-1.3.0
    cd example
    java -jar start.jar

You'll need to revise your schema. You can generate this from your application
(once Haystack is installed and setup) by running 
``./manage.py build_solr_schema``. Take the output from that command and place
it in ``apache-solr-1.3.0/example/solr/conf/schema.xml``. Then restart Solr.

You'll also need a Solr binding, ``pysolr``. The development version can be
grabbed from GitHub via http://github.com/toastdriven/pysolr/tree/master. In the
near future, this should be merged into the main ``pysolr`` package and
distributed via PyPI. Place ``pysolr.py`` somewhere on your ``PYTHONPATH``.

More Like This
--------------

To enable the "More Like This" functionality in Haystack, you'll need
to enable the ``MoreLikeThisHandler``. Add the following line to your
``solrconfig.xml`` file within the ``config`` tag::

    <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />

Spelling Suggestions
--------------------

To enable the spelling suggestion functionality in Haystack, you'll need
to setup the ``MoreLikeThisHandler``. Add the following line to your
``solrconfig.xml`` file within the ``config`` tag::

    <searchComponent name="spellcheck" class="solr.SpellCheckComponent">

        <str name="queryAnalyzerFieldType">textSpell</str>

        <lst name="spellchecker">
          <str name="name">default</str>
          <str name="field">text</str>
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

Be warned that the ``<str name="field">text</str>`` portion will be specific to
your ``SearchIndex`` classes (in this case, assuming the main field is called
``text``). This should be the same as the ``<defaultSearchField>`` in your
``schema.xml``.


Whoosh
======

Official Download Location: http://whoosh.ca/

Whoosh is pure Python, so it's a great option for getting started quickly and
for development, though it does work for small scale live deployments. With the
upcoming 0.3.x release (as of 2009/08/31, the ``0.3.0b21`` is suitable for use),
Whoosh has become much more performant, stable and better tested. You can
install via PyPI_ via::

    sudo easy_install whoosh
    # ... or ...
    sudo pip install whoosh

Alternatively, you can use the following fork that is guaranteed to work with
Haystack but may be a revision or two behind::

    git clone http://github.com/toastdriven/whoosh.git
    cd whoosh
    sudo python setup.py install

This fork may eventually disappear entirely once it seems that Whoosh is fully
stable. When that time comes, this documentation will be updated.

.. _PyPI: http://pypi.python.org/pypi/Whoosh/


Xapian
======

Official Download Location: http://xapian.org/download

Xapian is written in C++ so it requires compilation (unless your OS has a
package for it). Installation looks like::

    curl -O http://oligarchy.co.uk/xapian/1.0.11/xapian-core-1.0.11.tar.gz
    curl -O http://oligarchy.co.uk/xapian/1.0.11/xapian-bindings-1.0.11.tar.gz
    
    tar xvzf xapian-core-1.0.11.tar.gz
    tar xvzf xapian-bindings-1.0.11.tar.gz
    
    cd xapian-core-1.0.11
    ./configure
    make
    sudo make install
    
    cd ..
    cd xapian-bindings-1.0.11
    ./configure
    make
    sudo make install

Xapian is a supported backend but is not included in Haystack proper due to
licensing. You can download the source from
http://github.com/notanumber/xapian-haystack/tree/master. Installation
instructions can be found on that page as well. The backend, written
by David Sauve (notanumber), fully implements the `SearchQuerySet` API and is
an excellent alternative to Solr.