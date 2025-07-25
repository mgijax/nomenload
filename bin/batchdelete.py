'''
#
# Purpose:
#
#	1) To delete a list of existing Markers
#	    MRK_Marker
#	    MGI_History
#
# Input:
#
#	A tab-delimited file in the format:
#
#   1. MGI ID
#   2. Symbol
#   3. J#
#   4. Event reason, for example, “sequence removed by provider”
#   5. Submitter
#
# lec	05/01/2025
#	- wts2-1656/Batch Delete
#
'''

import sys
import os
import db
import mgi_utils
import loadlib

#db.setTrace()

DEBUG = 0

#
# from configuration file
#
mode = os.environ['NOMENMODE']
inputFileName = os.environ['DELETE_FILE_DEFAULT']
diagFileName = os.environ['DELETE_LOG_DIAG']
errorFileName = os.environ['DELETE_LOG_ERROR']

inputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor
lineNum = 0

eventReasonLookup = {}

markerID = ''
symbol = ''
jnum = ''
eventReason = ''
createdBy = ''
markerKey = ''
refKey = ''
eventReasonKey = ''
createdByKey = ''

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

    db.commit()
    db.useOneConnection()

    if message is not None:
        sys.stderr.write('\n' + str(message) + '\n')

    try:
        inputFile.close()
        diagFile.flush()
        errorFile.flush()
        diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.close()
        errorFile.close()
    except:
        pass

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

    global inputFile, diagFile, diagFileName
    global errorFile, errorFileName
    global eventReasonLookup

    db.useOneConnection(1)

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

    results = db.sql('select * from VOC_Term where _vocab_key = 34', 'auto')
    for r in results:
        key = r['term']
        value = r['_term_key']
        eventReasonLookup[key] = []
        eventReasonLookup[key].append(value)
    #print(eventReasonLookup)

    # Log all SQL 
    db.set_sqlLogFunction(db.sqlLogAll)

    # Set Log File Descriptor
    db.set_commandLogFile(diagFileName)

    # Set Log File Descriptor
    diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
    diagFile.write('Server: %s\n' % (db.get_sqlServer()))
    diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))
    diagFile.write('Input File: %s\n' % (inputFileName))

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
    elif mode not in ['load']:
        exit(1, 'Invalid Processing Mode:  %s\n' % (mode))

def sanityCheck():
    '''
    #
    # requires:
    #
    # effects:
    #
    # returns:
    #	0 if sanity check passes
    #	1 if sanity check fails
    #
    '''

    global markerKey
    global refKey
    global eventReasonKey
    global createdByKey

    error = 0

    markerKey = loadlib.verifyMarker(markerID, lineNum, None)
    refKey = loadlib.verifyReference(jnum, lineNum, None)
    createdByKey = loadlib.verifyUser(createdBy, lineNum, None)

    if eventReason not in eventReasonLookup:
        eventReasonKey = 0
    else:
        eventReasonKey = eventReasonLookup[eventReason][0]

    if markerKey != 0:
        results = db.sql(''' select * from mrk_marker where _marker_key = %s and symbol = '%s' ''' % (markerKey, symbol), 'auto')
        if len(results) == 0:
                errorFile.write('\nMarker ID, Symbol Do Not Match: ' + markerID + ', ' + symbol + '\n')
                error = 1

    if markerKey != 0:
        results = db.sql(''' select * from mrk_marker where _marker_status_key = 2 and _marker_key = %s ''' % (markerKey), 'auto')
        if len(results) == 1:
                errorFile.write('\nMarker ID Already Withdrawn: ' + markerID + ', ' + symbol + '\n')
                error = 1

    if markerKey != 0:
        results = db.sql(''' select * from all_allele where _marker_key = %s ''' % (markerKey), 'auto')
        if len(results) >= 1:
                errorFile.write('\nMarker ID contains an Allele: ' + markerID + ', ' + symbol + '\n')
                error = 1

    if markerKey == 0 or \
       refKey == 0 or \
       eventReasonKey == 0 or \
       createdByKey == 0:
        error = 1

    return (error)

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

    global lineNum
    global markerID
    global symbol 
    global jnum
    global eventReason
    global createdBy

    # For each line in the input file

    for line in inputFile.readlines():

        lineNum = lineNum + 1

        # Split the line into tokens
        tokens = str.split(line[:-1], '\t')

        try:
            markerID = tokens[0]
            symbol = tokens[1].replace("'", "''")
            jnum = tokens[2]
            eventReason = tokens[3]
            createdBy = tokens[4]
        except:
            errorFile.write('Invalid Line (missing column(s)) (row %d): %s\n' % (lineNum, line))
            continue

        #
        # sanity checks
        #

        if sanityCheck() == 1:
            errorFile.write(str(tokens) + '\n\n')
            continue

        cmd = '''select * from MRK_deleteWithdrawal(%s,%s,%s,%s);\n''' \
                % (createdByKey, markerKey, refKey, eventReasonKey)
        diagFile.write(cmd)

        if not DEBUG:
                db.sql(cmd, None)
                db.commit()

    # end of "for line in inputFile.readlines():"

#
# Main
#

#print 'init()'
init()

#print 'verifyMode()'
verifyMode()

#print 'processFile()'
processFile()
