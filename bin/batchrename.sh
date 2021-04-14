#!/bin/sh
#
#  batchrename.sh
###########################################################################
#
#  Purpose:
# 	This script runs the Nomenclature Batch Rename load
#
  Usage=batchrename.sh
#
#  Env Vars:
#
#      See the configuration file batchrename.config
#
#  Inputs:
#
#      - configuration file - batchrename.config
#      - input file - see batchrename.config
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables 
#      - batchrename logs and bcp file to ${OUTPUTDIR}
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
#      6) Load batchrename using configuration file
#      7) Load mappingload using configuration file
#      8) Archive the input file.
#      9) Touch the "lastrun.batchrename" file to timestamp the last run of the load.
#
# History:
#
# lec	09/28/2015
#	- new (using batchrename as a template)
#

cd `dirname $0`

#
# Verify and source the configuration file
#
CONFIG_FILE=$1
. ${CONFIG_FILE}

MAIL_LOADNAME="${NOMENMODE} : Batch Rename Load"
export MAIL_LOADNAME

# change names to ${LOG}
LOG_FILE=${RENAME_LOG_FILE} 
LOG_PROC=${RENAME_LOG_PROC} 
LOG_DIAG=${RENAME_LOG_DIAG} 
LOG_CUR=${RENAME_LOG_CUR} 
LOG_VAL=${RENAME_LOG_VAL} 
LOG_ERROR=${RENAME_LOG_ERROR}
export LOG_FILE LOG_PROC LOG_DIAG LOG_CUR LOG_VAL LOG_ERROR

rm -rf ${RENAME_LOG_FILE} ${RENAME_LOG_PROC} ${RENAME_LOG_DIAG} ${RENAME_LOG_CUR} ${RENAME_LOG_VAL} ${RENAME_LOG_ERROR}

#
# use user-provied value or use config/default value
# Make sure the input file exists (regular file or symbolic link).
#
if [ $# -eq 2 ] 
then
    RENAME_FILE_DEFAULT=$2
fi
if [ ! -r ${RENAME_FILE_DEFAULT} ]
then
    echo "Missing input file: ${RENAME_FILE_DEFAULT}" | tee -a ${RENAME_LOG_FILE}
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
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${RENAME_LOG_FILE}
        exit 1
    fi  
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${RENAME_LOG_FILE}
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
    startLog ${RENAME_LOG_PROC} ${RENAME_LOG_DIAG} ${RENAME_LOG_CUR} ${RENAME_LOG_VAL} | tee -a ${RENAME_LOG}
    getConfigEnv >> ${RENAME_LOG_PROC}
    getConfigEnv -e >> ${RENAME_LOG_DIAG}
fi

#
# There should be a "lastrun.batchrename" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
if [ ${NOMENMODE} != "preview" ]
then
    LASTRUN_FILE=${INPUTDIR}/lastrun.batchrename

    if [ -f ${LASTRUN_FILE} ]
    then
        if test ${LASTRUN_FILE} -nt ${RENAME_FILE_DEFAULT}
        then
            echo "SKIPPED: ${NOMENMODE} : Input file has not been updated" | tee -a ${RENAME_LOG_FILE_PROC}
	    exit 0
        fi
    fi
fi

#
# Convert the input file into a QC-ready version that can be used to run
# the sanity/QC reports against.
#
dos2unix ${RENAME_FILE_DEFAULT} ${RENAME_FILE_DEFAULT} 2>/dev/null

#
# Execute nomen load
#
echo "" | tee -a ${RENAME_LOG_FILE}
date | tee -a ${RENAME_LOG_FILE}
echo "Running batchrename : ${NOMENMODE}" | tee -a ${RENAME_LOG_FILE}
cd ${OUTPUTDIR}
${PYTHON} ${NOMENLOAD}/bin/batchrename.py | tee -a ${RENAME_LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${NOMENLOAD} ${CONFIG_FILE} : ${NOMENMODE} :"

#
# set permissions
#
case `whoami` in
    mgiadmin)
	chmod -f 775 ${FILEDIR}/*
	chgrp -f mgi ${FILEDIR}/*
	chgrp -f mgi ${FILEDIR}/*/*
	chmod -f 775 ${DESTFILEDIR}/*
	chgrp -f mgi ${DESTFILEDIR}/*
	chgrp -f mgi ${DESTFILEDIR}/*/*
	chgrp -f mgi ${NOMENLOAD}/bin
	chgrp -f mgi ${NOMENLOAD}/bin/batchrename.log
	;;
esac

#
# Archive : publshed only
# dlautils/preload with archive
#
if [ ${NOMENMODE} != "preview" ]
then
    createArchive ${ARCHIVEDIR} ${RENAME_LOGDIR} ${RENAMEDIR} ${OUTPUTDIR} | tee -a ${RENAME_LOG}
fi 

#
# Touch the "lastrun.batchrename" file to note when the load was run.
#
if [ ${NOMENMODE} != "preview" ]
then
    touch ${LASTRUN_FILE}
fi

#
# cat the error file
#
cat ${RENAME_LOG_ERROR}

echo "" | tee -a ${RENAME_LOG_FILE}
date | tee -a ${RENAME_LOG_FILE}

#
# run postload cleanup and email logs
#
if [ ${NOMENMODE} != "preview" ]
then
    JOBKEY=0;export JOBKEY
    shutDown
fi

