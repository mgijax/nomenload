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

cd ${NOMENDATADIR}

rm -rf ${NOMENLOG}
touch ${NOMENLOG}
 
date >> ${NOMENLOG}
 
#
# Execute nomenload
#
echo "Updating markers in: ${NOMENDATAFILE} to Marker Type Key: ${NEWMKRTYPE} \
	Updated By: ${MODIFIEDBY}" | tee -a ${NOMENLOG}
echo ${MGD_DBSERVER} | tee -a  ${NOMENLOG}
echo ${MGD_DBNAME} | tee -a ${NOMENLOG}
${NOMENLOAD}/bin/updateMkrType.py >& ${NOMENLOG}
set returnStatus=$status
if ( $returnStatus ) then
    echo "Marker Type Update ${CONFIGFILE}: FAILED" | tee -a ${NOMENLOG}
else
    echo "Marker Type Update ${CONFIGFILE}: SUCCESSFUL" | tee -a ${NOMENLOG}
endif

date >> ${NOMENLOG}

