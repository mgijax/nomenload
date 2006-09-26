#!/usr/local/bin/python

'''
#
# Purpose:
#
#	To generate a batch file for obsoleting genes that only have
#	associations to "deleted" Sequences
#
# Output:
#
#       Batch file:
#
#	field 1: MGI ID
#	field 2: same MGI ID
#	field 3: Symbol
#	field 4: Name
#
# lec	09/07/2006
#	- created
#
'''
import sys
import os
import string
import db
import mgi_utils

#globals

TAB = '\t'
CRT = '\n'

outputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor

outputFileName = os.environ['INPUTFILE']
diagFileName = ''	# file name
errorFileName = ''	# file name

 
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
	# 1. Initializes file descriptors/open files
	#
	# returns:
	#
	'''
 
	global outputFile, diagFile, errorFile, outputFileName, errorFileName, diagFileName
 
	db.useOneConnection(1)
	diagFileName = outputFileName + '.diagnostics'
	errorFileName = outputFileName + '.error'

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
		
	# Log all SQL
	db.set_sqlLogFunction(db.sqlLogAll)

	# Set Log File Descriptor
	db.set_sqlLogFD(diagFile)

	diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
	diagFile.write('Server: %s\n' % (db.get_sqlServer()))
	diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))

	errorFile.write('Start Date/Time: %s\n\n' % (mgi_utils.date()))

def process():

	# deleted Sequences 

	db.sql('select s._Sequence_key into #deleted from SEQ_Sequence s where s._SequenceStatus_key = 316343', None)
	db.sql('create index idx1 on #deleted(_Sequence_key)', None)

	# deleted sequences annotated to mouse markers 

	db.sql('select ma.accID, m.symbol, m.name, c._Sequence_key, c._Marker_key, c._Refs_key ' + \
		'into #mdeleted ' + \
		'from #deleted d, SEQ_Marker_Cache c, ACC_Accession ma, MRK_Marker m ' + \
		'where d._Sequence_key = c._Sequence_key ' + \
		'and c._Marker_key = ma._Object_key  ' + \
		'and ma._MGIType_key = 2 ' + \
		'and ma._LogicalDB_key = 1 ' + \
		'and ma.prefixPart = "MGI:" ' + \
		'and ma.preferred = 1 ' + \
		'and c._Marker_key = m._Marker_key ' + \
		'and m._Marker_Status_key != 2 ' + \
		'and m.name like "gene model%" ', None)

	db.sql('create index idx1 on #mdeleted(_Sequence_key)', None)
	db.sql('create index idx2 on #mdeleted(_Marker_key)', None)

	# all non-deleted sequences for markers 
	# excluding DoTS (36), NIA (53), TIGR (35)

	db.sql('select c._Sequence_key, c._Marker_key ' + \
		'into #allmarkers ' + \
		'from #mdeleted m, SEQ_Marker_Cache c ' + \
		'where m._Marker_key = c._Marker_key ' + \
		'and c._LogicalDB_key not in (35, 36, 53) ' + \
		'and not exists (select 1 from #deleted d ' + \
		'where c._Sequence_key = d._Sequence_key)', None)

	db.sql('create index idx1 on #allmarkers(_Sequence_key)', None)
	db.sql('create index idx2 on #allmarkers(_Marker_key)', None)

	# deleted sequences annotated to mouse markers where deleted sequences are its only sequences

	results = db.sql('select distinct m.accID, m.symbol, m.name ' + \
		'from #mdeleted m ' + \
		'where not exists (select 1 from #allmarkers c ' + \
		'where m._Marker_key = c._Marker_key ' + \
		'and c._Sequence_key != m._Sequence_key) order by symbol', 'auto')

	for r in results:
	    outputFile.write(r['accID'] + TAB)
	    outputFile.write(r['accID'] + TAB)
	    outputFile.write(r['symbol'] + TAB)
	    outputFile.write(r['name'] + CRT)

#
# Main
#

init()
process()
exit(0)

