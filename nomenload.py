#!/usr/local/bin/python

'''
#
# Purpose:
#
#	To load new gene records into Nomen structures:
#	MRK_Nomen
#	MRK_Nomen_Reference
#	MRK_Nomen_Other
#	ACC_Accession
#	ACC_AccessionReference
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
#		field 6: J: (without the J:, just #####)
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
#	-M = mode (load, preview)
#	-I = input file
#	-G = MGD database
#	-B = bcp on
#
#	processing modes:
#		load - load the data
#
#		preview - perform all record verifications but do not load the data or
#		          make any changes to the database.  used for testing or to preview
#			  the load.
#
# Output:
#
#       5 BCP files:
#
#       MRK_Nomen.bcp                   master Nomen records
#       MRK_Nomen_Reference.bcp         Nomen/Reference records
#       MRK_Nomen_Other.bcp             Nomen/Other Name records
#       ACC_Accession.bcp               Accession records
#       ACC_AccessionReference.bcp      Accession/Reference records
#
#	Diagnostics file of all input parameters and SQL commands
#	Error file
#
# Processing:
#
#	1. Verify Mode.
#		if mode = load:  process records
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

#globals

DEBUG = 0		# set DEBUG to false unless preview mode is selected
nomenDB = ''		# Nomen database
bcpon = 0		# can the bcp files be bcp-ed into the database?  default is no.

inputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor
nomenFile = ''		# file descriptor
refFile = ''		# file descriptor
otherFile = ''		# file descriptor
accFile = ''		# file descriptor
accrefFile = ''		# file descriptor

diagFileName = ''	# file name
errorFileName = ''	# file name
passwordFileName = ''	# file name
nomenFileName = ''	# file name
refFileName = ''	# file name
otherFileName = ''	# file name
accFileName = ''	# file name
accrefFileName = ''	# file name

mode = ''		# processing mode
nomenKey = 0		# MRK_Nomen._Nomen_key
accKey = 0		# ACC_Accession._Accession_key
otherKey = 0		# MRK_Nomen_Other._Other_key
mgiKey = 0		# ACC_AccessionMax.maxNumericPart

typeDict = {}		# dictionary of marker types for quick lookup
statusDict = {}		# dictionary of marker statuses for quick lookup
referenceDict = {}	# dictionary of references for quick lookup
logicalDBDict = {}	# dictionary of logical DBs for quick lookup

markerEvent = 1                         # Assigned
markerEventReason = -1                  # Not Specified
mgiTypeKey = 1                          # Nomenclature
mgiPrefix = "MGI:"

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
		'-N Nomen database\n' + \
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
 
	global inputFile, diagFile, errorFile, errorFileName, diagFileName, passwordFileName
	global nomenFileName, refFileName, otherFileName, accFileName, accrefFileName
	global nomenFile, refFile, otherFile, accFile, accrefFile
	global mode
	global nomenKey, accKey, otherKey, mgiKey
	global bcpon, nomenDB
 
	try:
		optlist, args = getopt.getopt(sys.argv[1:], 'S:D:U:P:M:N:I:B')
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
                elif opt[0] == '-N':
                        nomenDB = opt[1]
                elif opt[0] == '-B':
                        bcpon = 1
                else:
                        showUsage()

	# User must specify Server, Database, User and Password
	password = string.strip(open(passwordFileName, 'r').readline())
	if server == '' or \
	   database == '' or \
	   user == '' or \
	   password == '' or \
	   mode == '' or \
	   inputFileName == '' or \
	   nomenDB == '':
		showUsage()

	# Initialize db.py DBMS parameters
	db.set_sqlLogin(user, password, server, database)
	db.useOneConnection(1)
 
	fdate = mgi_utils.date('%m%d%Y')	# current date
	head, tail = os.path.split(inputFileName) 
	diagFileName = tail + '.' + fdate + '.diagnostics'
	errorFileName = tail + '.' + fdate + '.error'
	nomenFileName = tail + '.MRK_Nomen.bcp'
	refFileName = tail + '.MRK_Nomen_Reference.bcp'
	otherFileName = tail + '.MRK_Nomen_Other.bcp'
	accFileName = tail + '.ACC_Accession.bcp'
	accrefFileName = tail + '.ACC_AccessionReference.bcp'

	try:
		inputFile = open(inputFileName, 'r')
	except:
		exit(1, 'Could not open file %s\n' % inputFileName)
		
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
		otherFile = open(otherFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % otherFileName)
		
	try:
		accFile = open(accFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % accFileName)
		
	try:
		accrefFile = open(accrefFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % accrefFileName)
		
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

	global DEBUG

	if mode == 'preview':
		DEBUG = 1
		bcpon = 0
	elif mode != 'load':
		exit(1, 'Invalid Processing Mode:  %s\n' % (mode))

def verifyReference(referenceID, lineNum):
	'''
	# requires:
	#	referenceID - the Accession ID of the Reference (J:)
	#	lineNum - the line number of the record from the input file
	#
	# effects:
	#	verifies that the Reference exists by checking the referenceDict
	#	dictionary for the reference ID or the database.
	#	writes to the error file if the Reference is invalid
	#	adds the Reference ID/Key to the global referenceDict dictionary if the
	#	reference is valid
	#
	# returns:
	#	0 if the Reference is invalid
	#	Reference Key if the Reference is valid
	#
	'''

	global referenceDict

	if referenceDict.has_key(referenceID):
		referenceKey = referenceDict[referenceID]
	else:
		referenceKey = accessionlib.get_Object_key('J:' + referenceID, 'Reference')
		if referenceKey is None:
			errorFile.write('Invalid Reference (%d): %s\n' % (lineNum, referenceID))
			referenceKey = 0
		else:
			referenceDict[referenceID] = referenceKey

	return(referenceKey)

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

def verifyMarkerType(markerType, lineNum):
	'''
	# requires:
	#	markerType - the Marker Type
	#	lineNum - the line number of the record from the input file
	#
	# effects:
	#	verifies that:
	#		the Marker Type exists 
	#	writes to the error file if the Marker Type is invalid
	#
	# returns:
	#	0 if the Marker Type is invalid
	#	Marker Type Key if the Marker Type is valid
	#
	'''

	markerTypeKey = 0

	if typeDict.has_key(markerType):
		markerTypeKey = typeDict[markerType]
	else:
		errorFile.write('Invalid Marker Type (%d) %s\n' % (lineNum, markerType))
		markerTypeKey = 0

	return(markerTypeKey)

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

def verifySubmittedBy(submittedBy, lineNum):
	'''
	# requires:
	#	submittedBy - the submittedBy (string)
	#	lineNum - the line number of the record from the input file
	#
	# effects:
	#	verifies that the Submitted By is non-numm
	#	writes to the error file if the Submitted By is invalid
	#
	# returns:
	#	0 if the Submitted By is invalid
	#	1 if the Submitted By is valid
	#
	'''

	if len(submittedBy) == 0:
		errorFile.write('Missing Submitted By for line: %d\n' % (lineNum))
		return(0)

	return(1)

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

	global nomenKey, accKey, mgiKey, otherKey

        results = db.sql('select maxKey = max(_Nomen_key) + 1 from %s..MRK_Nomen' % (nomenDB), 'auto')
        if results[0]['maxKey'] is None:
                nomenKey = 1000
        else:
                nomenKey = results[0]['maxKey']

        results = db.sql('select maxKey = max(_Accession_key) + 1 from %s..ACC_Accession' % (nomenDB), 'auto')
        if results[0]['maxKey'] is None:
                accKey = 1000
        else:
                accKey = results[0]['maxKey']

        results = db.sql('select maxKey = max(_Other_key) + 1 from %s..MRK_Nomen_Other' % (nomenDB), 'auto')
        if results[0]['maxKey'] is None:
                otherKey = 1000
        else:
                otherKey = results[0]['maxKey']

        results = db.sql('select maxKey = maxNumericPart + 1 from ACC_AccessionMax ' + \
		'where prefixPart = "%s"' % (mgiPrefix), 'auto')
        mgiKey = results[0]['maxKey']

def loadDictionaries():
	'''
	# requires:
	#
	# effects:
	#	loads global dictionaries: typeDict, statusDict, logicalDBDict
	#	for quicker lookup
	#
	# returns:
	#	nothing
	'''

	global typeDict, statusDict, logicalDBDict

	results = db.sql('select _Marker_Status_key, status from %s..MRK_Status' % (nomenDB), 'auto')
	for r in results:
		statusDict[r['status']] = r['_Marker_Status_key']

	results = db.sql('select _Marker_Type_key, name from MRK_Types', 'auto')
	for r in results:
		typeDict[r['name']] = r['_Marker_Type_key']

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

	global nomenKey, accKey, mgiKey, otherKey

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
			submittedBy = tokens[9]
		except:
			exit(1, 'Invalid Line (%d): %s\n' % (lineNum, line))

		markerTypeKey = verifyMarkerType(markerType, lineNum)
		markerStatusKey = verifyMarkerStatus(markerStatus, lineNum)
		referenceKey = verifyReference(jnum, lineNum)

		# other acc ids
		for otherAcc in string.split(otherAccIDs, '|'):
			if len(otherAcc) > 0:
				[logicalDB, acc] = string.split(otherAcc, ':')
				logicalDBKey = verifyLogicalDB(logicalDB, lineNum)
				if logicalDBKey > 0:
					otherAccDict[acc] = logicalDBKey
				else:
					error = 1

		if markerTypeKey == 0 or markerStatusKey == 0 or \
			referenceKey == 0 or \
			not verifySubmittedBy(submittedBy, lineNum):

			# set error flag to true
			error = 1

		# if errors, continue to next record
		if error:
			continue

		# if no errors, process the marker

		nomenFile.write('%d|%d|%d|%d|%d|%s||%s|%s|%s||%s||%s|%s\n' \
                	% (nomenKey, markerTypeKey, markerStatusKey, markerEvent, markerEventReason, \
                           submittedBy, symbol, name, chromosome, mgi_utils.prvalue(notes), cdate, cdate))

        	refFile.write('%d|%s|1|1|%s|%s\n' % (nomenKey, referenceKey, cdate, cdate))

		# MGI Accession ID for the marker

        	accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s\n' \
                	% (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, nomenKey, mgiTypeKey, cdate, cdate, cdate))
        	accKey = accKey + 1
        	mgiKey = mgiKey + 1

		# other names
		for o in string.split(synonyms, '|'):
			if len(o) > 0:
				otherFile.write('%d|%d|%s|%s|0|%s|%s\n' \
					% (otherKey, nomenKey, referenceKey, o, cdate, cdate))
				otherKey = otherKey + 1

		# accession ids

		for acc in otherAccDict.keys():
			prefixpart, numericpart = accessionlib.split_accnum(acc)
			accFile.write('%d|%s|%s|%s|%d|%d|%d|0|1|%s|%s|%s\n' \
                               	% (accKey, acc, prefixpart, numericpart, otherAccDict[acc], nomenKey, \
				   mgiTypeKey, cdate, cdate, cdate))
			accrefFile.write('%d|%s|%s|%s|%s\n' % (accKey, referenceKey, cdate, cdate, cdate))
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
	otherFile.close()
	accFile.close()
	accrefFile.close()

	bcp1 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, nomenDB, \
	   	'MRK_Nomen', nomenFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp2 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, nomenDB, \
	   	'MRK_Nomen_Reference', refFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp3 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, nomenDB, \
	   	'MRK_Nomen_Other', otherFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp4 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, nomenDB, \
	   	'ACC_Accession', accFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	bcp5 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, nomenDB, \
	   	'ACC_AccessionReference', accrefFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	diagFile.write('%s\n' % bcp1)
	diagFile.write('%s\n' % bcp2)
	diagFile.write('%s\n' % bcp3)
	diagFile.write('%s\n' % bcp4)
	diagFile.write('%s\n' % bcp5)

	os.system(bcp1)
	db.sql('dump transaction %s with truncate_only' % (db.get_sqlDatabase()), None)
	os.system(bcp2)
	db.sql('dump transaction %s with truncate_only' % (db.get_sqlDatabase()), None)
	os.system(bcp3)
	db.sql('dump transaction %s with truncate_only' % (db.get_sqlDatabase()), None)
	os.system(bcp4)
	db.sql('dump transaction %s with truncate_only' % (db.get_sqlDatabase()), None)
	os.system(bcp5)
	db.sql('dump transaction %s with truncate_only' % (db.get_sqlDatabase()), None)

#
# Main
#

init()
verifyMode()
setPrimaryKeys()
loadDictionaries()
processFile()
bcpFiles()
exit(0)

