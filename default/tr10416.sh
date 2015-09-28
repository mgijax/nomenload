#!/bin/sh

#
# usage: tr10416.sh newMarkerTypeKey createdByKey fullPathtoInputFile
#

#
#  If the MGICONFIG environment variable does not have a local override,
#  use the default "live" settings.
#
if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

cd `dirname $0`
LOG=`pwd`/tr10416.log
rm -f ${LOG}

# parameter one: new marker type key
#Gene = 1
#DNA Segment = 2
#Pseudogene = 7
#Other Genome Features = 9
#NEWMARKERTYPE=$1
NEWMARKERTYPE=7
# parameter two: user key
# yz = 1093
# cjb = 1041
BYWHOM=1093

# parameter three: full path to input file
INFILE_NAME=/mgi/all/wts_projects/10400/10416/GeneToPseudogene_Gm.txt

export NEWMARKERTYPE BYWHOM INFILE_NAME

echo ${MGD_DBSERVER}
echo ${MGD_DBNAME}
echo "Updating marker type to marker type ${NEWMARKERTYPE} by user \
    ${BYWHOM} from input file ${INFILE_NAME}"
date | tee ${LOG} 
echo 'Running update script' | tee -a ${LOG}
./tr10416.py >> ${LOG} 2>&1
echo 'Done running update script' | tee -a ${LOG}
date | tee -a ${LOG}
