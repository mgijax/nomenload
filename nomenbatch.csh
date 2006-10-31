#!/bin/csh -f

#
# Process batch withdrawals
#
# Usage:  nomenbatch.csh configFile
#

setenv CONFIGFILE $1

cd `dirname $0` && source ./${CONFIGFILE}

source ${EI}/Configuration
cd ${EI}/mgd

${NOMENBATCH} -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGI_DBUSER} -P${MGI_DBPASSWORDFILE} -I${INPUTFILE} --refKey=${REFKEY} --eventKey=${EVENTKEY} --eventReasonKey=${EVENTREASONKEY} --addAsSynonym=${ADDASSYNONYM}

