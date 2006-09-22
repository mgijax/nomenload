#!/bin/csh -f

#
# broadcast genes from nomen to MGI
#
# Usage:  broadcast.csh configFile
#
# Assumes that genes were loaded into Nomen previously
#

setenv CONFIGFILE $1

cd `dirname $0` && source ./${CONFIGFILE}

cd ${NOMENDATADIR}

rm -rf ${NOMENLOG}
touch ${NOMENLOG}
 
date >> ${NOMENLOG}
 
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
and b.accID = "${NOMENREFERENCE}"
and n._NomenStatus_key = t._Term_key
and term = "${NOMENSTATUS}"
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

#
# Execute mapping load
#

cd ${MAPPINGLOAD}
${MAPPINGLOAD}/mappingload.csh ${NOMENLOAD}/${CONFIGFILE}

date >> ${NOMENLOG}

