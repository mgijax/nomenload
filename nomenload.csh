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

#declare marker_cursor cursor for
#select n._Nomen_key
#from NOM_Marker n, MGI_Reference_Assoc r
#where n._Nomen_key = r._Object_key
#and r._MGIType_key = 21
#and r._Refs_key = 85878
#for read only
#go

#declare @nomenKey integer
#
#open marker_cursor
#
#fetch marker_cursor into @nomenKey
#
#while (@@sqlstatus = 0)
#begin
#        exec NOM_transferToMGD @nomenKey, "official"
#        fetch marker_cursor into @nomenKey
#end
#
#close marker_cursor
#deallocate cursor marker_cursor

