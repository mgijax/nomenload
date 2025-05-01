#!/bin/sh
#
#  batchdelete.sh
###########################################################################
#
#  Purpose:
# 	This script runs the Nomenclature Batch Delete load
#
  Usage=batchdelete.sh
#
#
# History:
#
# lec	05/01/2025
#	- wts2-1656/Batch Delete
#

cd `dirname $0`

#
# Verify and source the configuration file
#
CONFIG_FILE=$1
. ${CONFIG_FILE}

MAIL_LOADNAME="${NOMENMODE} : Batch Delete Load"
export MAIL_LOADNAME

# change names to ${LOG}
LOG_FILE=${DELETE_LOG_FILE} 
LOG_PROC=${DELETE_LOG_PROC} 
LOG_DIAG=${DELETE_LOG_DIAG} 
LOG_CUR=${DELETE_LOG_CUR} 
LOG_VAL=${DELETE_LOG_VAL} 
LOG_ERROR=${DELETE_LOG_ERROR}
export LOG_FILE LOG_PROC LOG_DIAG LOG_CUR LOG_VAL LOG_ERROR

rm -rf ${DELETE_LOG_FILE} ${DELETE_LOG_PROC} ${DELETE_LOG_DIAG} ${DELETE_LOG_CUR} ${DELETE_LOG_VAL} ${DELETE_LOG_ERROR}

#
# use user-provied value or use config/default value
# Make sure the input file exists (regular file or symbolic link).
#
if [ $# -eq 2 ] 
then
    DELETE_FILE_DEFAULT=$2
fi
if [ ! -r ${DELETE_FILE_DEFAULT} ]
then
    echo "Missing input file: ${DELETE_FILE_DEFAULT}" | tee -a ${DELETE_LOG_FILE}
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
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${DELETE_LOG_FILE}
        exit 1
    fi  
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${DELETE_LOG_FILE}
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
    startLog ${DELETE_LOG_PROC} ${DELETE_LOG_DIAG} ${DELETE_LOG_CUR} ${DELETE_LOG_VAL} | tee -a ${DELETE_LOG}
    getConfigEnv >> ${DELETE_LOG_PROC}
    getConfigEnv -e >> ${DELETE_LOG_DIAG}
fi

#
# There should be a "lastrun.batchdelete" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
if [ ${NOMENMODE} != "preview" ]
then
    LASTRUN_FILE=${INPUTDIR}/lastrun.batchdelete

    if [ -f ${LASTRUN_FILE} ]
    then
        if test ${LASTRUN_FILE} -nt ${DELETE_FILE_DEFAULT}
        then
            echo "SKIPPED: ${NOMENMODE} : Input file has not been updated" | tee -a ${DELETE_LOG_FILE_PROC}
	    exit 0
        fi
    fi
fi

#
# Convert the input file into a QC-ready version that can be used to run
# the sanity/QC reports against.
#
dos2unix ${DELETE_FILE_DEFAULT} ${DELETE_FILE_DEFAULT} 2>/dev/null

#
# Execute nomen load
#
echo "" | tee -a ${DELETE_LOG_FILE}
date | tee -a ${DELETE_LOG_FILE}
echo "Running batchdelete : ${NOMENMODE}" | tee -a ${DELETE_LOG_FILE}
cd ${OUTPUTDIR}
${PYTHON} ${NOMENLOAD}/bin/batchdelete.py | tee -a ${DELETE_LOG_DIAG}
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
	chgrp -f mgi ${NOMENLOAD}/bin/batchdelete.log
	;;
esac

#
# Archive : publshed only
# dlautils/preload with archive
#
if [ ${NOMENMODE} != "preview" ]
then
    createArchive ${ARCHIVEDIR} ${DELETE_LOGDIR} ${DELETEDIR} ${OUTPUTDIR} | tee -a ${DELETE_LOG}
fi 

#
# Touch the "lastrun.batchdelete" file to note when the load was run.
#
if [ ${NOMENMODE} != "preview" ]
then
    touch ${LASTRUN_FILE}
fi

#
# cat the error file
#
cat ${DELETE_LOG_ERROR}

echo "" | tee -a ${DELETE_LOG_FILE}
date | tee -a ${DELETE_LOG_FILE}

#
# run postload cleanup and email logs
#
if [ ${NOMENMODE} != "preview" ]
then
    JOBKEY=0;export JOBKEY
    shutDown
fi

