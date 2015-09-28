#!/bin/csh -f

#
# default configuration file
#

if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
  
${NOMENLOAD}/bin/nomenload.csh /home/lec/mgi/dataload/nomenload/tr12109.nomen.config

date |tee -a $LOG

