#!/bin/csh -f

#
# Template
#

#setenv MGICONFIG /usr/local/mgi/live/mgiconfig
#setenv MGICONFIG /usr/local/mgi/test/mgiconfig
#source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
 
#cat - <<EOSQL | doisql.csh $MGD_DBSERVER $MGD_DBNAME $0 | tee -a $LOG
#
#use $MGD_DBNAME
#go
#
#checkpoint
#go
#
#end
#
#EOSQL

${NOMENLOAD}/bin/nomenload.csh ${NOMENLOAD}/tr11664.config | tee -a ${LOG}
${NOMENLOAD}/bin/nomenbatch.csh ${NOMENLOAD}/tr11664.nomenbatch.config | tee -a ${LOG}
#${NOMENLOAD}/bin/nomenbatch.csh ${NOMENLOAD}/tr11664.nomenbatch2.config

#${MIRBASELOAD/bin/mirbaseload.sh | tee -a ${LOG}

date |tee -a $LOG

