#!/bin/csh -f

#
# broadcast genes from nomen to MGI
#
# Usage:  broadcast.csh fullPathToConfigFile
#
# sc - 12/07/2007 - updated to take full path to configfile
#
# Assumes that genes were loaded into Nomen previously
#

setenv CONFIGFILE $1

cd `dirname $0` && source ${CONFIGFILE}

cd ${INPUTDIR}

rm -rf ${LOG_FILE}
touch ${LOG_FILE}
 
date >> ${LOG_FILE}
 
echo "Broadcasting symbols..." | tee -a ${LOG_FILE}

cat - <<EOSQL | doisql.csh $0 | tee -a ${LOG_FILE}

DECLARE
marker_cursor refcursor;
userKey integer;
nomenKey integer;

OPEN marker_cursor FOR
select n._ModifiedBy_key, n._Nomen_key
from NOM_Marker n, MGI_Reference_Assoc r, ACC_Accession b, VOC_Term t
where n._Nomen_key = r._Object_key
and r._MGIType_key = 21
and r._Refs_key = b._Object_key
and b._MGIType_key = 1
and b.accID = '${NOMENREFERENCE}'
and n._NomenStatus_key = t._Term_key
and term = '${NOMENSTATUS}'
;
LOOP
FETCH marker_cursor INTO userKey, nomenKey;
EXIT WHEN NOT FOUND;
PERFORM NOM_transferToMGD (userKey, nomenKey, 'official');
END LOOP;
CLOSE marker_cursor;

EOSQL

#
# Execute mapping load
#

cd ${MAPPINGLOAD}
${MAPPINGLOAD}/mappingload.csh ${CONFIGFILE}

date >> ${LOG_FILE}

