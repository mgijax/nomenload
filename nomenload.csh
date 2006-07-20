#!/bin/csh -f

#
# Example Wrapper script to create & load new genes into Nomen
#
# Usage:  nomenload.csh configFile
#

cd `dirname $0` && source $1

setenv NOMENLOAD	${DATALOAD}/nomenload/nomenload.py

cd ${NOMENDATADIR}

rm -rf ${NOMENLOG}
touch ${NOMENLOG}
 
date >> ${NOMENLOG}
 
#
# Execute nomenload
#
${NOMENLOAD} -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} -I${NOMENDATAFILE} -M${NOMENMODE} | tee -a ${NOMENLOG}

#
# Broadcast Genes from Nomen to MGI (NOM_ tables to MRK_ tables)
#

if ( ${NOMENBROADCAST} == "yes" ) then

echo "Broadcasting symbols..." | tee -a ${NOMENLOG}

cat - <<EOSQL | doisql.csh ${MGD_DBSERVER} ${MGD_DBNAME} $0 | tee -a ${NOMENLOG}

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

endif

date >> ${NOMENLOG}

