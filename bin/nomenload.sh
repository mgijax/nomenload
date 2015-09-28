#!/bin/sh
#
#  nomenload.sh
###########################################################################
#
#  Purpose:
# 	This script runs the Nomenclature & Mapping load
#
  Usage=nomenload.sh
#
#  Env Vars:
#
#      See the configuration file nomenload.config
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - configuration file - nomenload.config
#      - input file - see nomenload.config
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG_DIAG}, ${LOG_CUR} and ${LOG_VAL}
#      - nomenload logs and bcp file to ${OUTPUTDIR}
#      - mappingload logs and bcp files  - see mappingload
#      - Records written to the database tables
#      - Exceptions written to standard error
#      - Configuration and initialization errors are written to a log file
#        for the shell script
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal error occurred
#
#  Assumes:  Nothing
#
#      This script will perform following steps:
#
#      1) Validate the arguments to the script.
#      2) Source the configuration file to establish the environment.
#      3) Verify that the input files exist.
#      4) Initialize the log file.
#      5) Determine if the input file has changed since the last time that
#         the load was run. Do not continue if the input file is not new.
#      6) Load nomenload using configuration file
#      7) Archive the input file.
#      8) Touch the "lastrun" file to timestamp the last run of the load.
#
# History:
#
# lec	09/28/2015
#	- new (using nomenload as a template)
#

cd `dirname $0`
LOG=`pwd`/nomenload.log
rm -rf ${LOG}

RUNTYPE=live

CONFIG_LOAD=$1
INPUT_FILE_DEFAULT=$2

#
# Verify and source the configuration file
#
if [ ! -r ${CONFIG_LOAD} ]
then
   echo "Cannot read configuration file: ${CONFIG_LOAD}"
    exit 1   
fi

. ${CONFIG_LOAD}

#
# Make sure the input file exists (regular file or symbolic link).
#
if [ "`ls -L ${INPUT_FILE_DEFAULT} 2>/dev/null`" = "" ]
then
    echo "Missing input file: ${INPUT_FILE_DEFAULT}"
    exit 1
fi

#
# Create a temporary file and make sure that it is removed when this script
# terminates.
#
TMP_FILE=/tmp/`basename $0`.$$
touch ${TMP_FILE}
trap "rm -f ${TMP_FILE}" 0 1 2 15

#####################################
#
# Main
#
#####################################

#
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${INPUTDIR}/lastrun

if [ -f ${LASTRUN_FILE} ]
then
    if test ${LASTRUN_FILE} -nt ${INPUT_FILE_DEFAULT}
    then
        echo "Input file has not been updated - skipping load" | tee -a ${LOG_PROC}
	exit 0
    fi
fi

#
# run nomen load
#
echo "" >> ${LOG_DIAG}
date >> ${LOG_DIAG}
echo "Running Nomen load" >> ${LOG_DIAG}
cd ${OUTPUTDIR}
${NOMENLOAD}/bin/nomenload.py >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${NOMENLOAD} ${CONFIG_LOAD}"

#
# Archive a copy of the input file, adding a timestamp suffix.
#
echo "" >> ${LOG_DIAG}
date >> ${LOG_DIAG}
echo "Archive input file" | tee -a ${LOG_DIAG}
TIMESTAMP=`date '+%Y%m%d.%H%M'`
ARC_FILE=`basename ${INPUT_FILE_DEFAULT}`.${TIMESTAMP}
cp -p ${INPUT_FILE_DEFAULT} ${ARCHIVEDIR}/${ARC_FILE}

#
# Touch the "lastrun" file to note when the load was run.
#
touch ${LASTRUN_FILE}

