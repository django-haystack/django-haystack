#!/bin/bash
set -e

# this script is run in the container as setup

CONFDEST=/opt/solr/server/solr/configsets/collection1/conf/
BASIC_CONFIGS=/opt/solr/server/solr/configsets/basic_configs/conf/

# put configuration in place:
mkdir -p $CONFDEST
cp -r /confdir/* $CONFDEST


# borrow some files from the basic_configs configset:
cp -r $BASIC_CONFIGS/lang $CONFDEST
cp -r $BASIC_CONFIGS/*.txt $CONFDEST
cp -r $BASIC_CONFIGS/{currency,elevate}.xml $CONFDEST

ls -la $CONFDEST/

precreate-core collection1 $CONFDEST/../
precreate-core mgmnt
exec solr-foreground
