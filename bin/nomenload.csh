#!/bin/csh -f

#
# Load new genes into Nomen
# Load Mapping records
#
# Usage:  nomenload.csh fullPathToConfigFile
#
# sc - 12/07/2007 - updated to take full path to configfile
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

${NOMENLOAD}/bin/nomenload.py
set returnStatus=$status
if ( $returnStatus ) then
    echo "Nomen Load ${CONFIGFILE}: FAILED" | tee -a ${NOMENLOG}
else
    echo "Nomen Load ${CONFIGFILE}: SUCCESSFUL" | tee -a ${NOMENLOG}
endif

#
#
# Execute mapping load
#
# Only execute if we have broadcast the markers OR if we are just previewing
# the mapping
if ( $returnStatus == 0	&& ( ${NOMENMODE} == 'broadcast' || \
	${MAPPINGMODE} == 'preview' )) then
    # Don't try to execute if file  is empty
    if ( -z ${MAPPINGDATAFILE} ) then
	echo "Mapping File is empty, skipping mapping load" | tee -a ${NOMENLOG}
	date >> ${NOMENLOG}
	exit 0 
    endif

    # run mappingload
    cd ${MAPPINGLOAD}
    ${MAPPINGLOAD}/mappingload.csh ${CONFIGFILE}
    set returnStatus=$status
    if ( $returnStatus ) then
		echo "Mapping Load ${CONFIGFILE}: FAILED" | tee -a ${NOMENLOG}
    else
	echo  "Mapping Load ${CONFIGFILE}: SUCCESSFUL" | tee -a ${NOMENLOG}
    endif
else
    echo "Skipping mapping load: nomenload exit status = \
	$returnStatus Nomen Mode = ${NOMENMODE}" | tee -a ${NOMENLOG}
endif

date >> ${NOMENLOG}

