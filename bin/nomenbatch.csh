#!/bin/csh -f

#
# Process batch withdrawals
#
# Usage:  nomenbatch.csh fullPathToConfigFile
#
# sc - 12/07/2007 - updated to take full path to configfile
#

setenv CONFIGFILE $1

cd `dirname $0` && source ${CONFIGFILE}

source ${EI_USRLOCALMGI}/ei/Configuration

# must cd into directory
cd ${PG_DBUTILS}/bin/ei

# run EI NOMENBATCH script
${NOMENBATCH} -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} -I${INPUT_FILE_DEFAULT} --refKey=${REFKEY} --eventKey=${EVENTKEY} --eventReasonKey=${EVENTREASONKEY} --addAsSynonym=${ADDASSYNONYM}

