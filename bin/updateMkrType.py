#!/usr/local/bin/python

# update a set of markers to marker type ${NEWMARKERTYPE}
# update modification date
# update modified by ${BYWHOM}

import sys
import os
import string
import db
import mgi_utils
import accessionlib
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

for line in inputFile.readlines():
    tokens = string.split(line[:-1], '\t')
    mgiID = string.strip(tokens[0])
    results = db.sql('''
	select distinct a.accID, m.symbol
	from ACC_Accession a, MRK_Marker m 
        where a.accID = '%s' 
        and a._MGIType_key = 2
        and a._Object_key = m._Marker_key
	''' % (mgiID), 'auto')

    if len(results) == 0:
        print 'Invalid Marker MGI ID: %s' % mgiID
        continue
    cmd = '''
	update MRK_Marker
	set _Marker_Type_key = %s, 
	modification_date = "%s", 
        _ModifiedBy_key = %s 
	from ACC_Accession a, MRK_Marker m 
	where a.accID = '%s' 
	and a._MGIType_key = 2
	and a._Object_key = m._Marker_key
	''' % (newMkrTypeKey, loaddate, modifiedByKey, mgiID)

    db.sql(cmd, 'auto')

inputFile.close()

db.useOneConnection(0)
