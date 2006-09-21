#!/bin/csh -f

#
# Load new genes into Nomen
# Load Mapping records
#
# Usage:  nomenload.csh configFile
#

setenv CONFIGFILE $1

cd `dirname $0` && source ./${CONFIGFILE}

cd ${NOMENDATADIR}

rm -rf ${NOMENLOG}
touch ${NOMENLOG}
 
date >> ${NOMENLOG}
 
#
# Execute nomenload
#
${NOMENLOAD}/nomenload.py -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} -I${NOMENDATAFILE} -M${NOMENMODE} | tee -a ${NOMENLOG}

#
# Execute mapping load
#

cd ${MAPPINGLOADDIR}
${MAPPINGLOAD}/mappingload.csh ${NOMENLOADDIR}/${CONFIGFILE} | tee -a ${NOMENLOG}

date >> ${NOMENLOG}

