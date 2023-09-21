# update a set of markers to marker type 
# update modification date
# update modified by 

import sys
import os
import db
import mgi_utils
import loadlib

#
# from configuration file
#
user = os.environ['MGD_DBUSER']
passwordFileName = os.environ['MGD_DBPASSWORDFILE']
loaddate = loadlib.loaddate
modifiedBy = os.environ['MODIFIEDBY']
modifiedByKey = None
newMkrType = os.environ['NEWMKRTYPE']
newMkrTypeKey = None
db.useOneConnection(1)
db.set_sqlUser(user)
db.set_sqlPasswordFromFile(passwordFileName)
db.set_sqlLogFunction(db.sqlLogAll)
inputFileName = os.environ['NOMENDATAFILE']
inputFile = None          # file descriptor
updateList = [] # list of marker keys to update
mgiToMrkKeyDict = {} # {mgiID:markerKey, ...}
try:
        inputFile = open(inputFileName, 'r')
except:
    exit(1, 'Could not open file %s\n' % inputFileName)

#
# get keys for  NEWMKRTYPE and MODIFIEDBY
#
results = db.sql('''select _Marker_Type_key from MRK_Types where name = '%s' ''' % newMkrType, 'auto')
if len(results) == 0:
    exit (1, 'Invalid marker type  %s\n' % newMkrType)
newMkrTypeKey = results[0]['_Marker_Type_key']

results = db.sql('''select _User_key from MGI_User where login = '%s' ''' % modifiedBy, 'auto')
if len(results) == 0:
    exit (1, 'Invalid user login %s\n' % modifiedBy)
modifiedByKey = results[0]['_User_key']

#
# Create mouse marker MGI ID to marker key lookup
results = db.sql('''select a.accid, m._Marker_key
        from ACC_Accession a, MRK_Marker m
        where a._MGIType_key = 2
        and a._LogicalDB_key = 1
        and a.preferred = 1
        and a.prefixPart = 'MGI:'
        and a._Object_key = m._Marker_key
        and m._Organism_key = 1''', 'auto')
for r in results:
    mgiToMrkKeyDict[r['accid']] = r['_Marker_key']

# iterate thru the file creating list of marker keys to update
for line in inputFile.readlines():
    tokens = str.split(line[:-1], '\t')
    mgiID = str.strip(tokens[0])

    if mgiID not in mgiToMrkKeyDict:
        print('%s is not a valid mouse ID' % mgiID)
        exit (1, 'Invalid mouse ID %s\n' % mgiID)
    updateList.append(mgiToMrkKeyDict[mgiID])

for key in updateList:
    cmd = '''
        update MRK_Marker
        set _Marker_Type_key = %s, 
        modification_date = '%s', 
        _ModifiedBy_key = %s 
        where _Marker_key = %s''' % (newMkrTypeKey, loaddate, modifiedByKey, key)
    print(cmd)
    db.sql(cmd, 'auto')

db.commit()
inputFile.close()

db.useOneConnection(0)
