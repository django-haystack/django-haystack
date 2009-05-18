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

Finally, to enable the "More Like This" functionality in Haystack, you'll need
to enable the ``MoreLikeThisHandler``. Add the following line to your
``solrconfig.xml`` file within the ``config`` tag::

    <requestHandler name="/mlt" class="solr.MoreLikeThisHandler" />


Whoosh
======

Official Download Location: http://whoosh.ca/

Whoosh is pure Python, so it's a great option for getting started quickly. For
now (as of 2009/04/28), it requires a bit of patching (Whoosh version 0.1.15).
A forked version that ought to be stable for Haystack use can be found at
http://github.com/toastdriven/whoosh::

    git clone http://github.com/toastdriven/whoosh
    cd whoosh
    sudo python setup.py install

As Whoosh gains features and becomes more stable/performant, the hope is to
eventually defer to the main release and drop the fork entirely. When that
time comes, this documentation will be updated.


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