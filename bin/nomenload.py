#!/usr/local/bin/python

'''
#
# Purpose:
#
#	1) To load new gene records into Nomen structures:
#	    NOM_Marker
#	    MGI_Reference_Assoc
#	    MGI_Synonym
#	    ACC_Accession
#	    ACC_AccessionReference
#
# 	2) To create an input file for the mapping load
#
# 	3) To (optionally) broadcast them to MGI (MRK_Marker)
#
# Assumes:
#
#	That no one else is adding Nomen records to the database.
#
# Side Effects:
#
#	None
#
# Input:
#
#	A tab-delimited file in the format:
#		field 1: Marker Type
#		field 2: Symbol
#		field 3: Name
#		field 4: Chromosome
#		field 5: Marker Status
#		field 6: J: (J:#####)
#		field 7: List of Synonyms, separated by "|"
#		field 8: LogicalDB:Acc ID|LogicalDB:Acc ID|... (accession ids)
#		field 9: Nomenclature Notes
#		field 10: Submitted By
#
# Parameters:
#
#	processing modes:
#		load - load the data into Nomen structures
#
#		preview - perform all record verifications but do not load the 
#			data or make any changes to the database.
#
#		broadcast - load the data into Nomen structures and 
#			broadcast to MRK structures
#
#
# Output:
#
#       5 BCP files:
#
#       NOM_Marker.bcp                  master Nomen records
#       MGI_Reference_Assoc.bcp         Nomen/Reference records
#       MGI_Synonym.bcp             	Nomen Synonym records
#       ACC_Accession.bcp               Accession records
#       ACC_AccessionReference.bcp      Accession/Reference records
#
#	Diagnostics file of all input parameters and SQL commands
#	Error file
#
#	Mapping input file:
#		MGI AccID of Marker
#		Chromosome
#		yes (to automatically update the Marker's chromosome field)
#		Band (leave blank)
#		Assay Type
#		Description (leave blank)
#
# Processing:
#	See nomenload wiki:
#	http://prodwww.informatics.jax.org/software/wiki/index.php/Nomenload
#
# History:
#
# sc	09/16/2015 - TR12058 first test of nomenload since conversion to
#  	postgres - several changed needed. See HISTORY file
#
# sc    8/07 - updated comments, broke long lines while creating wiki
#
# lec	12/30/2003
#	- TR 5327; nomen merge
#
# lec	08/02/2002
#	- created
#
'''

import sys
import os
import string
import db
import mgi_utils
import accessionlib
import loadlib

#globals

#
# from configuration file
#
user = os.environ['MGD_DBUSER']
passwordFileName = os.environ['MGD_DBPASSWORDFILE']
mode = os.environ['NOMENMODE']
inputFileName = os.environ['INPUT_FILE_DEFAULT']
mappingFileName = os.environ['MAPPINGDATAFILE']
mappingCol5 = os.environ['MAPPINGASSAYTYPE']

DEBUG = 0		# set DEBUG to false unless preview mode is selected
bcpon = 1		# can the bcp files be bcp-ed into the database?  
			# default is yes.

inputFile = ''		# file descriptor
outputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor
nomenFile = ''		# file descriptor
refFile = ''		# file descriptor
synFile = ''		# file descriptor
accFile = ''		# file descriptor
accrefFile = ''		# file descriptor
mappingFile = ''	# file descriptor

diagFileName = ''	# file name
errorFileName = ''	# file name
nomenFileName = ''	# file name
refFileName = ''	# file name
synFileName = ''	# file name
accFileName = ''	# file name
accrefFileName = ''	# file name

startNomenKey = 0	# beginning NOM_Marker._Nomen_key
nomenKey = 0		# NOM_Marker._Nomen_key
accKey = 0		# ACC_Accession._Accession_key
synKey = 0		# MGI_Synonym._Synonym_key
mgiKey = 0		# ACC_AccessionMax.maxNumericPart
refAssocKey = 0		# MGI_Reference_Assoc._Assoc_key
createdByKey = 0

statusDict = {}		# dictionary of marker statuses for quick lookup
referenceDict = {}	# dictionary of references for quick lookup
logicalDBDict = {}	# dictionary of logical DBs for quick lookup

markerEvent = 1                         # Assigned
markerEventReason = -1                  # Not Specified
mgiTypeKey = 21                         # Nomenclature
mgiPrefix = "MGI:"
refAssocTypeKey = 1003			# Primary Reference
synTypeKey = 1008			# Other Synonym Type key

mappingCol3 = 'yes'			# update Mkr chr?
mappingCol4 = ''			# band (leave blank)
mappingCol6 = ''			# description ( leave blank)

cdate = mgi_utils.date('%m/%d/%Y')	# current date

def exit(status, message = None):
    '''
    # requires: status, the numeric exit status (integer)
    #           message (string)
    #
    # effects:
    # Print message to stderr and exits
    #
    # returns:
    #
    '''

    if message is not None:
	sys.stderr.write('\n' + str(message) + '\n')

    try:
	inputFile.close()
	outputFile.close()
	diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
	errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
	diagFile.close()
	errorFile.close()
    except:
	pass

    db.useOneConnection()
    sys.exit(status)
 
def init():
    '''
    # requires: 
    #
    # effects: 
    # 1. Processes command line options
    # 2. Initializes local DBMS parameters
    # 3. Initializes global file descriptors/file names
    #
    # returns:
    #
    '''

    global inputFile, outputFile, diagFile, errorFile
    global errorFileNamediagFileName, nomenFileName, refFileName
    global synFileName, accFileName, accrefFileName
    global nomenFile, refFile, synFile, accFile, accrefFile, mappingFile
    global startNomenKey, nomenKey, accKey, synKey, mgiKey, refAssocKey

    db.useOneConnection(1)
    db.set_sqlUser(user)
    db.set_sqlPasswordFromFile(passwordFileName)

    head, tail = os.path.split(inputFileName) 

    outputFileName = inputFileName + '.out'
    diagFileName = tail + '.diagnostics'
    errorFileName = tail + '.error'
    nomenFileName = tail + '.NOM_Marker.bcp'
    refFileName = tail + '.MGI_Reference_Assoc.bcp'
    synFileName = tail + '.MGI_Synonym.bcp'
    accFileName = tail + '.ACC_Accession.bcp'
    accrefFileName = tail + '.ACC_AccessionReference.bcp'

    try:
	inputFile = open(inputFileName, 'r')
    except:
	exit(1, 'Could not open file %s\n' % inputFileName)
	    
    try:
	outputFile = open(outputFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % outputFileName)
	    
    try:
	diagFile = open(diagFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % diagFileName)
	    
    try:
	errorFile = open(errorFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % errorFileName)
	    
    try:
	nomenFile = open(nomenFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % nomenFileName)
	    
    try:
	refFile = open(refFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % refFileName)
	    
    try:
	synFile = open(synFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % synFileName)
	    
    try:
	accFile = open(accFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % accFileName)
	    
    try:
	accrefFile = open(accrefFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % accrefFileName)
	    
    try:
	mappingFile = open(mappingFileName, 'w')
    except:
	exit(1, 'Could not open file %s\n' % mappingFileName)
	    
    # Log all SQL
    db.set_sqlLogFunction(db.sqlLogAll)

    # Set Log File Descriptor
    db.set_commandLogFile(diagFileName)
    diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
    diagFile.write('Server: %s\n' % (db.get_sqlServer()))
    diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))
    diagFile.write('Input File: %s\n' % (inputFileName))

    errorFile.write('Start Date/Time: %s\n\n' % (mgi_utils.date()))

def verifyMode():
    '''
    # requires:
    #
    # effects:
    #	Verifies the processing mode is valid.  If it is not valid,
    #	the program is aborted.
    #	Sets globals based on processing mode.
    #	Deletes data based on processing mode.
    #
    # returns:
    #	nothing
    #
    '''

    global DEBUG, bcpon

    if mode == 'preview':
	DEBUG = 1
	bcpon = 0
    elif mode not in ['load', 'broadcast']:
	exit(1, 'Invalid Processing Mode:  %s\n' % (mode))

def verifyMarkerStatus(markerStatus, lineNum):
    '''
    # requires:
    #	markerStatus - the Marker Status
    #	lineNum - the line number of the record from the input file
    #
    # effects:
    #	verifies that:
    #		the Marker Status exists 
    #	writes to the error file if the Marker Status is invalid
    #
    # returns:
    #	0 if the Marker Status is invalid
    #	Marker Status Key if the Marker Status is valid
    #
    '''

    markerStatusKey = 0

    if statusDict.has_key(markerStatus):
	markerStatusKey = statusDict[markerStatus]
    else:
	errorFile.write('Invalid Marker Status (%d) %s\n' % (lineNum, markerStatus))
	markerStatusKey = 0

    return(markerStatusKey)

def verifyDuplicateMarker(symbol, lineNum):
    '''
    # requires:
    #	symbol - the Marker Symbol
    #	lineNum - the line number of the record from the input file
    #
    # effects:
    #	verifies that:
    #		the Marker Symbol is not a duplicate
    #	writes to the error file if the Symbol is a duplicate
    #
    # returns:
    #	1 if the Marker Symbol is a duplicate
    #	0 if the Marker Symbol is not a duplicate
    #
    '''

    results = db.sql('''select _Nomen_key from NOM_Marker where symbol = '%s'
	union 
	select _Marker_key from MRK_Marker where _Organism_key = 1 and symbol = '%s'
	''' % (symbol, symbol), 'auto')

    if len(results) == 0:
	return 0
    else:
	errorFile.write('Duplicate Marker (%d) %s\n' % (lineNum, symbol))
	return 1

def verifyLogicalDB(logicalDB, lineNum):
    '''
    # requires:
    #	logicalDB - the logical database
    #	lineNum - the line number of the record from the input file
    #
    # effects:
    #	verifies that:
    #		the Logical DB exists 
    #	writes to the error file if the Logical DB is invalid
    #
    # returns:
    #	0 if the Logical DB is invalid
    #	Logical DB Key if the Logical DB is valid
    #
    '''

    logicalDBKey = 0

    if logicalDBDict.has_key(logicalDB):
	logicalDBKey = logicalDBDict[logicalDB]
    else:
	errorFile.write('Invalid Logical DB (%d) %s\n' % (lineNum, logicalDB))
	logicalDBKey = 0

    return(logicalDBKey)

def setPrimaryKeys():
    '''
    # requires:
    #
    # effects:
    #	Sets the global primary keys values needed for the load
    #
    # returns:
    #	nothing
    #
    '''

    global startNomenKey, nomenKey, accKey, mgiKey, synKey
    global refAssocKey

    results = db.sql('select max(_Nomen_key) + 1 as maxKey from NOM_Marker', 'auto')
    if results[0]['maxKey'] is None:
	nomenKey = 1000
    else:
	nomenKey = results[0]['maxKey']
    startNomenKey = nomenKey

    results = db.sql('select max(_Assoc_key) + 1 as maxKey from MGI_Reference_Assoc', 'auto')
    if results[0]['maxKey'] is None:
	refAssocKey = 1000
    else:
	refAssocKey = results[0]['maxKey']

    results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
    if results[0]['maxKey'] is None:
	accKey = 1000
    else:
	accKey = results[0]['maxKey']

    results = db.sql('select max(_Synonym_key) + 1 as maxKey from MGI_Synonym', 'auto')
    if results[0]['maxKey'] is None:
	synKey = 1000
    else:
	synKey = results[0]['maxKey']

    results = db.sql('select maxNumericPart + 1 as maxKey from ACC_AccessionMax where prefixPart = \'%s\'' % (mgiPrefix), 'auto')
    mgiKey = results[0]['maxKey']

def loadDictionaries():
    '''
    # requires:
    #
    # effects:
    #	loads global dictionaries: statusDict, logicalDBDict
    #	for quicker lookup
    #
    # returns:
    #	nothing
    '''

    global statusDict, logicalDBDict

    results = db.sql('select _Term_key, term from VOC_Term_NomenStatus_View', 'auto')
    for r in results:
	statusDict[r['term']] = r['_Term_key']

    results = db.sql('select _LogicalDB_key, name from ACC_LogicalDB', 'auto')
    for r in results:
	logicalDBDict[r['name']] = r['_LogicalDB_key']

def processFile():
    '''
    # requires:
    #
    # effects:
    #	Reads input file
    #	Verifies and Processes each line in the input file
    #
    # returns:
    #	nothing
    #
    '''

    global nomenKey, accKey, mgiKey, synKey, refAssocKey, createdByKey

    lineNum = 0
    # For each line in the input file

    for line in inputFile.readlines():

	error = 0
	lineNum = lineNum + 1
	otherAccDict = {}

	# Split the line into tokens
	tokens = string.split(line[:-1], '\t')

	try:
	    markerType = tokens[0]
	    symbol = tokens[1]
	    name = tokens[2]
	    chromosome = tokens[3]
	    markerStatus = tokens[4]
	    jnum = tokens[5]
	    synonyms = tokens[6]
	    otherAccIDs = tokens[7]
	    notes = tokens[8]
	    createdByKey = tokens[9]
	except:
	    exit(1, 'Invalid Line (%d): %s\n' % (lineNum, line))

	markerTypeKey = loadlib.verifyMarkerType(markerType, lineNum, errorFile)
	markerStatusKey = verifyMarkerStatus(markerStatus, lineNum)
	referenceKey = loadlib.verifyReference(jnum, lineNum, errorFile)
	createdByKey = loadlib.verifyUser(createdByKey, lineNum, errorFile)
	isDuplicateMarker = verifyDuplicateMarker(symbol, lineNum)

	# other acc ids
	for otherAcc in string.split(otherAccIDs, '|'):
	    if len(otherAcc) > 0:
		[logicalDB, acc] = string.split(otherAcc, ':')
		logicalDBKey = verifyLogicalDB(logicalDB, lineNum)
		if logicalDBKey > 0:
		    otherAccDict[acc] = logicalDBKey
		else:
		    error = 1

	if markerTypeKey == 0 or \
	    markerStatusKey == 0 or \
	    referenceKey == 0 or \
	    isDuplicateMarker == 1 or \
	    createdByKey == 0:

	    # set error flag to true
	    error = 1

	# if errors, continue to next record
	if error:
	    continue

	# if no errors, process the marker
	nomenFile.write('%d|%d|%d|%d|%d|%s|%s|%s||%s|||%s|%s|%s|%s\n' \
	    % (nomenKey, markerTypeKey, markerStatusKey, markerEvent, \
		markerEventReason, symbol, name, chromosome, mgi_utils.prvalue(notes), \
		createdByKey, createdByKey, cdate, cdate))

	refFile.write('%d|%d|%d|%d|%d|%s|%s|%s|%s\n' \
	    % (refAssocKey, referenceKey, nomenKey, mgiTypeKey, \
		refAssocTypeKey, createdByKey, createdByKey, cdate, cdate))

	# MGI Accession ID for the marker

	accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s|%s\n' \
	    % (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, nomenKey, \
		mgiTypeKey, createdByKey, createdByKey, cdate, cdate))

	# write record back out and include MGI Accession ID
	outputFile.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
	    % (markerType, symbol, name, chromosome, \
		markerStatus, jnum, mgi_utils.prvalue(synonyms), \
		mgi_utils.prvalue(otherAccIDs), \
		mgi_utils.prvalue(notes), createdByKey, \
		mgiPrefix + str(mgiKey)))

	# mapping record; write it out before incrementing the acc id keys

	mappingFile.write('%s%d|%s|%s|%s|%s|%s\n' \
	    % (mgiPrefix, mgiKey, chromosome, mappingCol3, mappingCol4, \
		mappingCol5, mappingCol6))

	accKey = accKey + 1
	mgiKey = mgiKey + 1
	refAssocKey = refAssocKey + 1

	# synonyms
	for o in string.split(synonyms, '|'):
	    if len(o) > 0:
		synFile.write('%d|%d|%d|%d|%s|%s|%s|%s|%s|%s\n' \
		    % (synKey, nomenKey, mgiTypeKey, synTypeKey, referenceKey, \
			o, createdByKey, createdByKey, cdate, cdate))
		synKey = synKey + 1

	# accession ids

	for acc in otherAccDict.keys():
	    prefixpart, numericpart = accessionlib.split_accnum(acc)
	    accFile.write('%d|%s|%s|%s|%d|%d|%d|0|1|%s|%s|%s|%s\n' \
		% (accKey, acc, prefixpart, numericpart, otherAccDict[acc], \
		    nomenKey, mgiTypeKey, createdByKey, createdByKey, \
		    cdate, cdate))
	    accrefFile.write('%d|%s|%s|%s|%s|%s\n' \
		% (accKey, referenceKey, createdByKey, createdByKey, \
		    cdate, cdate))
	    accKey = accKey + 1

	nomenKey = nomenKey + 1

    # end of "for line in inputFile.readlines():"

    #
    # Update the AccessionMax value
    #

    if not DEBUG:
	db.sql('select * from ACC_setMax (%d)' % (lineNum), None)
 	db.commit()

def bcpFiles():
    '''
    # requires:
    #
    # effects:
    #	BCPs the data into the database
    #
    # returns:
    #	nothing
    #
    '''

    if DEBUG or not bcpon:
	return

    nomenFile.close()
    refFile.close()
    synFile.close()
    accFile.close()
    accrefFile.close()
    mappingFile.close()

    bcpCommand = os.environ['PG_DBUTILS'] + '/bin/bcpin.csh'
    currentDir = os.getcwd()

    bcp1 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
	(bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'NOM_Marker', currentDir, nomenFileName)

    bcp2 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MGI_Reference_Assoc', currentDir, refFileName)

    bcp3 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MGI_Synonym', currentDir, synFileName)

    bcp4 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'ACC_Accession', currentDir, accFileName)

    bcp5 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'ACC_AccessionReference', currentDir, accrefFileName)

    diagFile.write('%s\n' % bcp1)
    diagFile.write('%s\n' % bcp2)
    diagFile.write('%s\n' % bcp3)
    diagFile.write('%s\n' % bcp4)
    diagFile.write('%s\n' % bcp5)

    os.system(bcp1)
    os.system(bcp2)
    os.system(bcp3)
    os.system(bcp4)
    os.system(bcp5)

def broadcastToMRK():
    '''
    # requires:
    #
    # effects:
    #	broadcasts the recently processed NOM markers to MGI
    #
    # returns:
    #	nothing
    #
    '''

    if mode != 'broadcast':
	return

    for x in range(startNomenKey, nomenKey):
	db.sql('select * from NOM_transferToMGD (%s, %s)' % (createdByKey, x), None)
	db.commit()

#
# Main
#

print 'init()'
init()
print 'verifyMode()'
verifyMode()
print 'setPrimaryKeys()'
setPrimaryKeys()
print 'loadDictionaries()'
loadDictionaries()
print 'processFile()'
processFile()
print 'bcpFiles()'
bcpFiles()
print 'broadcastToMRK'
broadcastToMRK()
exit(0)

