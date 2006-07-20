#!/bin/csh -f

#
# Example Wrapper script to create & load new genes into Nomen
#
# Usage:  nomenload.csh
#

cd `dirname $0` && source $1

setenv NOMENLOAD	${DATALOAD}/nomenload/nomenload.py
setenv LOG `basename $0`.log

cd ${NOMENDATADIR}

rm -rf ${LOG}
touch ${LOG}
 
date >> ${LOG}
 
#
# Execute nomenload
#
${NOMENLOAD} -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} -I${NOMENDATAFILE} -M${NOMENMODE} >>& ${LOG}

#
# Broadcast Genes from Nomen to MGI (NOM_ tables to MRK_ tables)
#

cat - <<EOSQL | doisql.csh ${MGD_DBSERVER} ${MGD_DBNAME} $0 >> $LOG

use ${MGD_DBNAME}
go

declare marker_cursor cursor for
select n._Nomen_key
from NOM_Marker n, MGI_Reference_Assoc r, ACC_Accession b, VOC_Term t
where n._Nomen_key = r._Object_key
and r._MGIType_key = 21
and r._Refs_key = b._Object_key
and b._MGIType_key = 1
and b.accID = ${NOMENREFERENCE}
and n._NomenStatus_key = t._Term_key
and term = "In Progress"
go

declare @nomenKey integer

open marker_cursor

fetch marker_cursor into @nomenKey

while (@@sqlstatus = 0)
begin
        exec NOM_transferToMGD @nomenKey, "official"
        fetch marker_cursor into @nomenKey
end

close marker_cursor
deallocate cursor marker_cursor

checkpoint
go

quit

EOSQL

date >> ${LOG}

