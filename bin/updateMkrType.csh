#!/bin/csh -f

#
# Update a marker's type, including user who modified the marker type
#
# Usage:  updateMkrType.csh fullPathToConfigFile
#
# sc - 10/21/2010 - new
#

setenv CONFIGFILE $1

cd `dirname $0` && source ${CONFIGFILE}

cd ${INPUTDIR}

rm -rf ${LOG_FILE}
touch ${LOG_FILE}
 
date >> ${LOG_FILE}
 
#
# Execute nomenload
#
echo "Updating markers in: ${NOMENDATAFILE} to Marker Type Key: ${NEWMKRTYPE} \
	Updated By: ${MODIFIEDBY}" | tee -a ${LOG_FILE}
echo ${MGD_DBSERVER} | tee -a  ${LOG_FILE}
echo ${MGD_DBNAME} | tee -a ${LOG_FILE}
${NOMENLOAD}/bin/updateMkrType.py >& ${LOG_FILE}
set returnStatus=$status
if ( $returnStatus ) then
    echo "Marker Type Update ${CONFIGFILE}: FAILED" | tee -a ${LOG_FILE}
else
    echo "Marker Type Update ${CONFIGFILE}: SUCCESSFUL" | tee -a ${LOG_FILE}
endif

date >> ${LOG_FILE}

