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

# source EI config file
source ${EI}/Configuration

# cd to EI directory where NOMENBATCH is found
cd ${EIUTILS}

# run EI NOMENBATCH script
${NOMENBATCH} -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGI_DBUSER} -P${MGI_DBPASSWORDFILE} -I${INPUTFILE} --refKey=${REFKEY} --eventKey=${EVENTKEY} --eventReasonKey=${EVENTREASONKEY} --addAsSynonym=${ADDASSYNONYM}

