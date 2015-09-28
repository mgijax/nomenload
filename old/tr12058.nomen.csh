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
  
${NOMENLOAD}/bin/nomenload.csh /home/lec/mgi2/dataload/nomenload/tr12058.nomen.config

# sc 9/11/15 - since we are running this from another script along with another
#     nomen load, I am moving these cache loads there.
#date | tee -a ${LOG}
#echo 'Load Marker/Label Cache Table' | tee -a ${LOG}
#${MRKCACHELOAD}/mrklabel.csh
#date | tee -a ${LOG}
#echo 'Load Marker/Reference Cache Table' | tee -a ${LOG}
#${MRKCACHELOAD}/mrkref.csh
#date | tee -a ${LOG}
#echo 'Load Marker/Location Cache Table' | tee -a ${LOG}
#${MRKCACHELOAD}/mrklocation.csh
#date | tee -a ${LOG}
#echo 'Load Marker/MCV Cache Table' | tee -a ${LOG}
#${MRKCACHELOAD}/mrkmcv.csh

date |tee -a $LOG

