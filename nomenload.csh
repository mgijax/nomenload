#!/bin/csh -f

#
# Wrapper script to create & load new genes into Nomen
#
# Usage:  nomenload.csh
#

cd `dirname $0`

# DB schema directory; its Configuration file will set up all you need
setenv SCHEMADIR $1
source ${SCHEMADIR}/Configuration

# Nomen load specific
setenv NOMENLOAD	/usr/local/mgi/dataload/nomenload/nomenload.py
setenv NOMENMODE	load
#setenv NOMENMODE	preview

# specific to your load
setenv DATADIR		specifictoyourload
setenv DATAFILE 	speciftoyourload

setenv LOG `basename $0`.log

rm -rf ${LOG}
touch ${LOG}
 
date >> ${LOG}
 
#
# Execute nomenload
#
${NOMENLOAD} -S${DBSERVER} -D${DBNAME} -U${DBUSER} -P${DBPASSWORDFILE} -I${{DATAFILE} -M${{NOMENMODE} >>& ${LOG}

date >> ${LOG}

