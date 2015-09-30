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
#      - configuration file - nomenload.config
#      - input file - see nomenload.config
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG_FILE}, ${LOG_FILE_CUR}, ${LOG_FILE_VAL}, ${LOG_ERROR}
#      - nomenload logs and bcp file to ${OUTPUTDIR}
#      - mappingload logs and bcp files  - see mappingload
#      - Records written to the database tables
#      - Exceptions written to standard error
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
#      7) Load mappingload using configuration file
#      8) Archive the input file.
#      9) Touch the "lastrun" file to timestamp the last run of the load.
#
# History:
#
# lec	09/28/2015
#	- new (using nomenload as a template)
#

cd `dirname $0`
LOG=`pwd`/nomenload.log
rm -rf ${LOG}

usage ()
{
    echo "Usage: nomenload.sh config_file input_file"
    echo "       where"
    echo "           config_file = path to the nomen configuration file"
    echo "           input_file = path to the nomen input file"
    exit 1
}

#
# Check usage
#

if [ ! $# -eq 2 ] 
then
    usage
fi

#
# Verify and source the configuration file
#
CONFIG_FILE=$1
if [ ! -r ${CONFIG_FILE} ]
then
   echo "Cannot read configuration file: ${CONFIG_FILE}" | tee -a ${LOG}
    exit 1   
fi

. ${CONFIG_FILE}

rm -rf ${LOG_FILE} ${LOG_PROC} ${LOG_DIAG} ${LOG_CUR} ${LOG_VAL} ${LOG_ERROR}

#
# Make sure the input file exists (regular file or symbolic link).
#
INPUT_FILE_DEFAULT=$2
if [ ! -r ${INPUT_FILE_DEFAULT} ]
then
    echo "Missing input file: ${INPUT_FILE_DEFAULT}" | tee -a ${LOG_FILE}
    exit 1
fi

#
#  Source the DLA library functions.
#

if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${LOG_FILE}
        exit 1
    fi  
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${LOG_FILE}
    exit 1
fi

#####################################
#
# Main
#
#####################################

#
# dlautils/preload minus jobstream & archive
#
if [ ${NOMENMODE} != "preview" ]
then
    startLog ${LOG_PROC} ${LOG_DIAG} ${LOG_CUR} ${LOG_VAL} | tee -a ${LOG}
    getConfigEnv >> ${LOG_PROC}
    getConfigEnv -e >> ${LOG_DIAG}
fi

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
        echo "SKIPPED: ${NOMENMODE} : Input file has not been updated" | tee -a ${LOG_FILE_PROC}
	exit 0
    fi
fi

#
# Execute nomen load
#
echo "" | tee -a ${LOG_FILE}
date | tee -a ${LOG_FILE}
echo "Running nomenload : ${NOMENMODE}" | tee -a ${LOG_FILE}
${NOMENLOAD}/bin/nomenload.py | tee -a ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${NOMENLOAD} ${CONFIG_FILE} : ${NOMENMODE} : "

#
#
# Execute mapping load IF:
# a) nomenload was successfull
#  and
# b) nomen:'broadcast' or mapping:'preview'
#
if [ ${STAT} == 0 ]
then
    if [[ ${NOMENMODE} == "broadcast" ]] || [[ ${MAPPINGMODE} == "preview" ]]
    then
        if [ ! -f ${MAPPINGDATAFILE} ] 
        then
            echo "SKIPPED: ${NOMENMODE} : Mapping File is empty" | tee -a ${LOG_FILE}
            date >> ${LOG_FILE}
            exit 1 
        fi

        ${MAPPINGLOAD}/mappingload.sh ${CONFIG_FILE}
        STAT=$?
        checkStatus ${STAT} "${MAPPINGLOAD} ${CONFIG_FILE} : ${MAPPINGMODE} : "
    fi
else
    echo "FATAL ERROR: nomenload exit status = ${STAT} : ${NOMENMODE}" | tee -a ${LOG_FILE}
fi

#
# Archive
# dlautils/preload with archive
#
#if [ ${NOMENMODE} != "preview" ]
#then
cp -p ${INPUT_FILE_DEFAULT} ${INPUTDIR}
createArchive ${ARCHIVEDIR} ${LOGDIR} ${INPUTDIR} ${OUTPUTDIR} | tee -a ${LOG}
#fi 

#
# Touch the "lastrun" file to note when the load was run.
#
touch ${LASTRUN_FILE}

#
# cat the error file
#
cat ${LOG_ERROR}

echo "" | tee -a ${LOG_FILE}
date | tee -a ${LOG_FILE}

#
# run postload cleanup and email logs
#
if [ ${NOMENMODE} != 'preview' ]
then
    JOBKEY=0;export JOBKEY
    shutDown
fi

