#!/usr/local/bin/python

'''
#
# Purpose:
#
#	To load new gene records into Nomen structures:
#	NOM_Marker
#	MGI_Reference_Assoc
#	MGI_Synonym
#	ACC_Accession
#	ACC_AccessionReference
#
# and to create an input file for the mapping load
#
# and to (optionally) broadcast them to MGI (MRK_Marker)
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
#	-S = database server
#	-D = database
#	-U = user
#	-P = password file
#	-M = mode (load, preview, broadcast)
#	-I = input file
#
#	processing modes:
#		load - load the data into Nomen structures
#
#		preview - perform all record verifications but do not load the data or
#		          make any changes to the database.  used for testing or to preview
#			  the load.
#
#		broadcast - load the data into Nomen structures and broadcast to MRK structures
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
#
#	1. Verify Mode.
#		if mode = load:  process records
#		if mode = broadcast:  process records and broadcast
#		if mode = preview:  set "DEBUG" to True
#
#	2. Load Marker Types and Marker Statuses into dictionaries for quicker lookup.
#
#	For each line in the input file:
#
#	1.  Verify the Marker Type is valid.
#	    If the verification fails, report the error and skip the record.
#
#	2.  Verify the Marker Status is valid.
#	    If the verification fails, report the error and skip the record.
#
#	3.  Verify the Logical DB is valid.
#	    If the verification fails, report the error and skip the record.
#
#	4.  Verify the J: is valid.
#	    If the verification fails, report the error and skip the record.
#	    If the verification succeeeds, store the Jnum/Key pair in a dictionary
#	    for future reference.
#
#	5.  Verify the Submitted By is provided (i.e. is not null).
#	    If the verification fails, report the error and skip the record.
#
#	6.  Create the Nomen record.
#
#	7.  If Synonyms are provided, then process them.
#
#	8.  If Accession ids are provided, then process them.
#
# History:
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
import getopt
import db
import mgi_utils
import accessionlib
import loadlib

#globals

DEBUG = 0		# set DEBUG to false unless preview mode is selected
bcpon = 1		# can the bcp files be bcp-ed into the database?  default is yes.

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
passwordFileName = ''	# file name
nomenFileName = ''	# file name
refFileName = ''	# file name
synFileName = ''	# file name
accFileName = ''	# file name
accrefFileName = ''	# file name
mappingFileName = os.environ['MAPPINGDATAFILE']

mode = ''		# processing mode
startNomenKey = 0	# beginning NOM_Marker._Nomen_key
nomenKey = 0		# NOM_Marker._Nomen_key
accKey = 0		# ACC_Accession._Accession_key
synKey = 0		# MGI_Synonym._Synonym_key
mgiKey = 0		# ACC_AccessionMax.maxNumericPart
refAssocKey = 0		# MGI_Reference_Assoc._Assoc_key
userKey = 0

statusDict = {}		# dictionary of marker statuses for quick lookup
referenceDict = {}	# dictionary of references for quick lookup
logicalDBDict = {}	# dictionary of logical DBs for quick lookup

markerEvent = 1                         # Assigned
markerEventReason = -1                  # Not Specified
curationStateKey = 0
mgiTypeKey = 21                         # Nomenclature
mgiPrefix = "MGI:"
refAssocTypeKey = 1003			# Primary Reference
synTypeKey = 1003			# Other Synonym Type key

mappingCol3 = 'yes'
mappingCol4 = ''
mappingCol5 = os.environ['MAPPINGASSAYTYPE']
mappingCol6 = ''

cdate = mgi_utils.date('%m/%d/%Y')	# current date

def showUsage():
	'''
	# requires:
	#
	# effects:
	# Displays the correct usage of this program and exits
	# with status of 1.
	#
	# returns:
	'''
 
	usage = 'usage: %s -S server\n' % sys.argv[0] + \
		'-D database\n' + \
		'-U user\n' + \
		'-P password file\n' + \
		'-M mode\n' + \
		'-I input file\n'
	exit(1, usage)
 
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
	# 4. Initializes global keys
	#
	# returns:
	#
	'''
 
	global inputFile, outputFile, diagFile, errorFile, errorFileName, diagFileName, passwordFileName
	global nomenFileName, refFileName, synFileName, accFileName, accrefFileName
	global nomenFile, refFile, synFile, accFile, accrefFile, mappingFile
	global mode
	global startNomenKey, nomenKey, accKey, synKey, mgiKey, refAssocKey
 
	try:
		optlist, args = getopt.getopt(sys.argv[1:], 'S:D:U:P:M:I:')
	except:
		showUsage()
 
	#
	# Set server, database, user, passwords depending on options
	# specified by user.
	#
 
	server = ''
	database = ''
	user = ''
	password = ''
 
	for opt in optlist:
                if opt[0] == '-S':
                        server = opt[1]
                elif opt[0] == '-D':
                        database = opt[1]
                elif opt[0] == '-U':
                        user = opt[1]
                elif opt[0] == '-P':
			passwordFileName = opt[1]
                elif opt[0] == '-M':
                        mode = opt[1]
                elif opt[0] == '-I':
                        inputFileName = opt[1]
                else:
                        showUsage()

	# User must specify Server, Database, User and Password
	password = string.strip(open(passwordFileName, 'r').readline())
	if server == '' or \
	   database == '' or \
	   user == '' or \
	   password == '' or \
	   mode == '' or \
	   inputFileName == '':
		showUsage()

	# Initialize db.py DBMS parameters
	db.set_sqlLogin(user, password, server, database)
	db.useOneConnection(1)
 
	fdate = mgi_utils.date('%m%d%Y')	# current date
	head, tail = os.path.split(inputFileName) 
        outputFileName = inputFileName + '.out'
	diagFileName = tail + '.' + fdate + '.diagnostics'
	errorFileName = tail + '.' + fdate + '.error'
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
	db.set_sqlLogFD(diagFile)

	diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
	diagFile.write('Server: %s\n' % (server))
	diagFile.write('Database: %s\n' % (database))
	diagFile.write('User: %s\n' % (user))
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

	results = db.sql('select _Nomen_key from NOM_Marker where symbol = "%s" ' % (symbol) + \
		'union ' +
		'select _Marker_key from MRK_Marker where _Organism_key = 1 and symbol = "%s"' % (symbol), 'auto')

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

	global startNomenKey, nomenKey, accKey, mgiKey, synKey, refAssocKey, curationStateKey

        results = db.sql('select maxKey = max(_Nomen_key) + 1 from NOM_Marker', 'auto')
        if results[0]['maxKey'] is None:
                nomenKey = 1000
        else:
                nomenKey = results[0]['maxKey']
        startNomenKey = nomenKey

        results = db.sql('select maxKey = max(_Assoc_key) + 1 from MGI_Reference_Assoc', 'auto')
        if results[0]['maxKey'] is None:
                refAssocKey = 1000
        else:
                refAssocKey = results[0]['maxKey']

        results = db.sql('select maxKey = max(_Accession_key) + 1 from ACC_Accession', 'auto')
        if results[0]['maxKey'] is None:
                accKey = 1000
        else:
                accKey = results[0]['maxKey']

        results = db.sql('select maxKey = max(_Synonym_key) + 1 from MGI_Synonym', 'auto')
        if results[0]['maxKey'] is None:
                synKey = 1000
        else:
                synKey = results[0]['maxKey']

        results = db.sql('select maxKey = maxNumericPart + 1 from ACC_AccessionMax ' + \
		'where prefixPart = "%s"' % (mgiPrefix), 'auto')
        mgiKey = results[0]['maxKey']

        results = db.sql('select _Term_key from VOC_Term_CurationState_View where term = "Internal"', 'auto')
        curationStateKey = results[0]['_Term_key']

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

	global nomenKey, accKey, mgiKey, synKey, refAssocKey, userKey

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
			userKey = tokens[9]
		except:
			exit(1, 'Invalid Line (%d): %s\n' % (lineNum, line))

		markerTypeKey = loadlib.verifyMarkerType(markerType, lineNum, errorFile)
		markerStatusKey = verifyMarkerStatus(markerStatus, lineNum)
		referenceKey = loadlib.verifyReference(jnum, lineNum, errorFile)
		userKey = loadlib.verifyUser(userKey, lineNum, errorFile)
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
			userKey == 0:

			# set error flag to true
			error = 1

		# if errors, continue to next record
		if error:
			continue

		# if no errors, process the marker

		nomenFile.write('%d|%d|%d|%d|%d|%d|%s|%s|%s||%s|||%s|%s|%s|%s\n' \
                	% (nomenKey, markerTypeKey, markerStatusKey, markerEvent, markerEventReason, curationStateKey, \
                           symbol, name, chromosome, mgi_utils.prvalue(notes), userKey, userKey, cdate, cdate))

        	refFile.write('%d|%d|%d|%d|%d|%s|%s|%s|%s\n' \
			% (refAssocKey, referenceKey, nomenKey, mgiTypeKey, refAssocTypeKey, userKey, userKey, cdate, cdate))

		# MGI Accession ID for the marker

        	accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s|%s\n' \
                	% (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, nomenKey, mgiTypeKey, userKey, userKey, cdate, cdate))

		# write record back out and include MGI Accession ID
		outputFile.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
			% (markerType, symbol, name, chromosome, \
			markerStatus, jnum, mgi_utils.prvalue(synonyms), \
			mgi_utils.prvalue(otherAccIDs), \
			mgi_utils.prvalue(notes), userKey, \
			mgiPrefix + str(mgiKey)))

		# mapping record; write it out before incrementing the acc id keys

		mappingFile.write('%s%d\t%s\t%s\t%s\t%s\t%s\n' \
			% (mgiPrefix, mgiKey, chromosome, mappingCol3, mappingCol4, mappingCol5, mappingCol6))

        	accKey = accKey + 1
        	mgiKey = mgiKey + 1
		refAssocKey = refAssocKey + 1

		# synonyms
		for o in string.split(synonyms, '|'):
			if len(o) > 0:
				synFile.write('%d|%d|%d|%d|%s|%s|%s|%s|%s|%s\n' \
					% (synKey, nomenKey, mgiTypeKey, synTypeKey, referenceKey, o, userKey, userKey, cdate, cdate))
				synKey = synKey + 1

		# accession ids

		for acc in otherAccDict.keys():
			prefixpart, numericpart = accessionlib.split_accnum(acc)
			accFile.write('%d|%s|%s|%s|%d|%d|%d|0|1|%s|%s|%s|%s\n' \
                               	% (accKey, acc, prefixpart, numericpart, otherAccDict[acc], nomenKey, \
				   mgiTypeKey, userKey, userKey, cdate, cdate))
			accrefFile.write('%d|%s|%s|%s|%s|%s\n' % (accKey, referenceKey, userKey, userKey, cdate, cdate))
			accKey = accKey + 1

		nomenKey = nomenKey + 1

#	end of "for line in inputFile.readlines():"

	#
	# Update the AccessionMax value
	#

	if not DEBUG:
		db.sql('exec ACC_setMax %d' % (lineNum), None)

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

	bcpdelim = "|"

	if DEBUG or not bcpon:
		return

	nomenFile.close()
	refFile.close()
	synFile.close()
	accFile.close()
	accrefFile.close()
	mappingFile.close()

	bcp1 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'NOM_Marker', nomenFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp2 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'MGI_Reference_Assoc', refFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp3 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'MGI_Synonym', synFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp4 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'ACC_Accession', accFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp5 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'ACC_AccessionReference', accrefFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

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
	    db.sql('exec NOM_transferToMGD %s, "official"' % (x), None)

#
# Main
#

init()
verifyMode()
setPrimaryKeys()
loadDictionaries()
processFile()
bcpFiles()
broadcastToMRK()
exit(0)

