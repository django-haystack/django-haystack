import os
import sys

from fabric.api import *
from django.core.management import call_command

test_dir = os.path.dirname(__file__)
sys.path.append(test_dir)


def test(*names):
    for name in names:
        os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings' % name
        call_command('test', name)


@task
def test_all():
    test_dirs = [path for path in os.listdir('.')
                 if os.path.isdir(path) and path != 'discovery']
    test(*test_dirs)


@task
def test_core():
    test('core')


@task
def test_overrides():
    test('overrides')


@task
def test_simple():
    test('simple')


@task
def test_discovery():
    test('discovery')


@task
def test_elasticsearch():
    test('elasticsearch_tests')


def lsudo(command):
    local("sudo %s" % command)

JETTY_DEFAULT = """\
JAVA_HOME=/usr/java/default
JAVA_OPTIONS="-Dsolr.solr.home=/usr/share/solr/example/solr $JAVA_OPTIONS"
JETTY_HOME=/usr/share/solr/example
JETTY_USER=solr
JETTY_LOGS=/var/log/solr
JAVA_HOME=/usr/lib/jvm/default-java
JDK_DIRS="/usr/lib/jvm/default-java /usr/lib/jvm/java-6-sun"
"""

JETTY_LOGGING = """\
<?xml version="1.0"?>
<!DOCTYPE Configure PUBLIC "-//Mort Bay Consulting//DTD Configure//EN" "http://jetty.mortbay.org/configure.dtd">
<!-- =============================================================== -->
<!-- Configure stderr and stdout to a Jetty rollover log file -->
<!-- this configuration file should be used in combination with -->
<!-- other configuration files. e.g. -->
<!-- java -jar start.jar etc/jetty-logging.xml etc/jetty.xml -->
<!-- =============================================================== -->
<Configure id="Server" class="org.mortbay.jetty.Server">
<New id="ServerLog" class="java.io.PrintStream">
<Arg>
<New class="org.mortbay.util.RolloverFileOutputStream">
<Arg><SystemProperty name="jetty.logs" default="."/>/yyyy_mm_dd.stderrout.log</Arg>
<Arg type="boolean">false</Arg>
<Arg type="int">90</Arg>
<Arg><Call class="java.util.TimeZone" name="getTimeZone"><Arg>GMT</Arg></Call></Arg>
<Get id="ServerLogName" name="datedFilename"/>
</New>
</Arg>
</New>
<Call class="org.mortbay.log.Log" name="info"><Arg>Redirecting stderr/stdout to <Ref id="ServerLogName"/></Arg></Call>
<Call class="java.lang.System" name="setErr"><Arg><Ref id="ServerLog"/></Arg></Call>
<Call class="java.lang.System" name="setOut"><Arg><Ref id="ServerLog"/></Arg></Call>
</Configure>
"""


@task
def install_solr():
    local("""curl `curl -q -s -S -L http://www.apache.org/dyn/closer.cgi?path=lucene/solr/3.6.0/apache-solr-3.6.0.tgz | sed -n '/^<p><a href="http/s/.*"\\(.*\\)".*/\\1/gp'` | tar xzf -""")
    lsudo("mkdir /usr/share/solr")
    lsudo("mv apache-solr-3.6.0 /usr/share/solr")
    lsudo("curl http://svn.codehaus.org/jetty/jetty/branches/jetty-6.1/bin/jetty.sh > /etc/init.d/jetty")
    lsudo("chmod 755 /etc/init.d/jetty")
    with open("/etc/default/jetty", "w") as jetty_default:
        jetty_default.write(JETTY_DEFAULT)
    lsudo("mkdir -p /var/log/solr")
    with open("/usr/share/solr/example/etc/jetty-logging.xml", "w") as jetty_logging:
        jetty_logging.write(JETTY_LOGGING)
    lsudo("useradd -d /usr/share/solr -s /bin/false solr")
    lsudo("chown solr:solr -R /usr/share/solr")
    lsudo("chown solr:solr -R /var/log/solr")
    lsudo("sudo cp solr_tests/solr_test_schema.xml /usr/share/solr/example/solr/conf/schema.xml")
