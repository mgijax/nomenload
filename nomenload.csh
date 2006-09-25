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
${NOMENLOAD}/nomenload.py | tee -a ${NOMENLOG}

#
# Execute mapping load
#

cd ${MAPPINGLOAD}
${MAPPINGLOAD}/mappingload.csh ${NOMENLOAD}/${CONFIGFILE} | tee -a ${NOMENLOG}

date >> ${NOMENLOG}

