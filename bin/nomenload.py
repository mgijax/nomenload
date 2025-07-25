'''
#
# Purpose:
#
#	1) To load new gene records into Marker structures:
#	    MRK_Marker
#	    MGI_Reference_Assoc
#	    MGI_Synonym
#	    ACC_Accession
#	    ACC_AccessionReference
#       VOC_Annot (_annottype_key = 1011, _vocab_key = 79)
#
# 	2) To create an input file for the mapping load
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
#		field 9: MCV Term
#		field 10: Nomenclature Notes
#		field 11: Submitted By
#
# Parameters:
#
#	processing modes:
#		load - load the data into Nomen structures
#
#		preview - perform all record verifications but do not load the 
#			data or make any changes to the database.
#
# Sanity Checks: see sanityCheck()
#
#        1)  Invalid Line (missing column(s))
#        2)  Invalid Marker Status
#        3)  Invalid Chromosome
#        4)  Invalid Logical DB
#        5)  Symbol is Official/Interim/Reserved
#        6)  Sequences without Logical DB
#	 7)  More than 1 Reference in input file
#        8)  WARNING: Symbol is Withdrawn
#        9)  WARNING: Sequence is associated with other Markers
#	 10) WARNING: Duplicate Symbol in input file (1st instance will be loaded)
#
# Output:
#
#       6 BCP files:
#
#       MRK_Marker.bcp                  master Nomen records
#       MGI_Reference_Assoc.bcp         Nomen/Reference records
#       MGI_Synonym.bcp             	Nomen Synonym records
#       ACC_Accession.bcp               Accession records
#       ACC_AccessionReference.bcp      Accession/Reference records
#       VOC_Annot.bcp                   MCV Annotations
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
# lec	01/07/2025
#   wts2-1591/eag-93/ENSEMBL gene 113
#   add field 9: MCV Term
#
# lec	09/29/2015
#	- TR11216/12070 
#	- add ability for curator (sophia) to run sanity checks
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
import db
import mgi_utils
import accessionlib
import loadlib

#db.setTrace()

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
diagFileName = os.environ['LOG_DIAG']
errorFileName = os.environ['LOG_ERROR']

DEBUG = 0		# set DEBUG to false unless preview mode is selected
bcpon = 1		# can the bcp files be bcp-ed into the database?  default is yes (1).

inputFile = ''		# file descriptor
outputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor
markerFile = ''		# file descriptor
refFile = ''		# file descriptor
synFile = ''		# file descriptor
accFile = ''		# file descriptor
accrefFile = ''		# file descriptor
mappingFile = ''	# file descriptor
mrkcurrentFile = ''	# file descriptor
historyFile = ''	# file descriptor
alleleFile = ''		# file descriptor
noteFile = ''		# file descriptor
mcvFile = ''		# file descriptor

markerFileName = ''	# file name
refFileName = ''	# file name
synFileName = ''	# file name
accFileName = ''	# file name
accrefFileName = ''	# file name
mrkcurrentFileName = ''	# file name
historyFileName = ''	# file name
alleleFileName = ''	# file name
noteFileName = ''	# file name
mcvFileName = ''	# file name

markerKey = 0		# MRK_Marker._Marker_key
accKey = 0		    # ACC_Accession._Accession_key
synKey = 0		    # MGI_Synonym._Synonym_key
mgiKey = 0		    # ACC_AccessionMax.maxNumericPart
refAssocKey = 0		# MGI_Reference_Assoc._Assoc_key
alleleKey = 0		# ALL_Allele._Allele_key
noteKey = 0		    # MGI_Note._Note_key
historyKey = 0      # MRK_History._Assoc_key
mappingKey = 0      # MLD_Expt_Marker._Assoc_key
mcvKey = 0          # VOC_Annot._Annot_key
mgiCount = 0

statusDict = {}		# dictionary of marker statuses for quick lookup
referenceDict = {}	# dictionary of references for quick lookup
logicalDBDict = {}	# dictionary of logical DBs for quick lookup
mcvDict = {}        # dictionary of mcv terms for quick lookup

markerEvent = 106563604                # Assigned
markerEventReason = 106563610          # Not Specified
mgiTypeKey = 2                         # Nomenclature
alleleTypeKey = 11
mgiPrefix = "MGI:"
refAssocTypeKey = 1018			       # General Reference
synTypeKey = 1004			           # Other Synonym Type key

mappingCol3 = 'yes'			# update Mkr chr?
mappingCol4 = ''			# band (leave blank)
mappingCol6 = ''			# description ( leave blank)

cdate = mgi_utils.date('%m/%d/%Y')	# current date

markerType = None
symbol = None
name = None
chromosome = None
markerStatus = None
jnum = None
synonyms = None
otherAccIDs = None
notes = None
createdBy = None
markerTypeKey = 0
markerStatusKey = 0
createdByKey = 0
referenceKey = 0
logicalDBKey = 0
mcvTermey = 0
otherAccDict = {}
markerLookup = []
referenceLookup = []

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
        errorFile.write('\nEnd file\n')
        diagFile.close()
        errorFile.close()
        outputFile.close()
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

    global inputFile, outputFile, diagFile, errorFile
    global errorFileName, diagFileName, markerFileName, refFileName
    global mrkcurrentFileName, historyFileName, alleleFileName, noteFileName, mcvFileName
    global synFileName, accFileName, accrefFileName
    global markerFile, refFile, synFile, accFile, accrefFile, mappingFile
    global mrkcurrentFile, historyFile, alleleFile, noteFile, mcvFile
    global markerKey, accKey, synKey, mgiKey, refAssocKey, alleleKey, noteKey, historyKey, mcvKey

    db.useOneConnection(1)
    db.set_sqlUser(user)
    db.set_sqlPasswordFromFile(passwordFileName)

    outputFileName = inputFileName + '.out'
    markerFileName = 'MRK_Marker.bcp'
    refFileName = 'MGI_Reference_Assoc.bcp'
    synFileName = 'MGI_Synonym.bcp'
    accFileName = 'ACC_Accession.bcp'
    accrefFileName = 'ACC_AccessionReference.bcp'
    mrkcurrentFileName = 'MRK_Current.bcp'
    historyFileName = 'MRK_History.bcp'
    alleleFileName = 'ALL_Allele.bcp'
    noteFileName = 'MGI_Note.bcp'
    mcvFileName = 'VOC_Annot.bcp'

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
        markerFile = open(markerFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % markerFileName)
            
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
            
    try:
        mrkcurrentFile = open(mrkcurrentFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % mrkcurrentFileName)
            
    try:
        historyFile = open(historyFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % historyFileName)
            
    try:
        alleleFile = open(alleleFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % alleleFileName)
            
    try:
        noteFile = open(noteFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % noteFileName)
            
    try:
        mcvFile = open(mcvFileName, 'w')
    except:
        exit(1, 'Could not open file %s\n' % mcvFileName)
            
    # Log all SQL 
    db.set_sqlLogFunction(db.sqlLogAll)

    # Set Log File Descriptor
    db.set_commandLogFile(diagFileName)

    # Set Log File Descriptor
    diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
    diagFile.write('Server: %s\n' % (db.get_sqlServer()))
    diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))
    diagFile.write('Input File: %s\n' % (inputFileName))
    errorFile.write('\nStart file: %s\n\n' % (mgi_utils.date()))

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
    elif mode not in ['load']:
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

    if markerStatus in statusDict:
        markerStatusKey = statusDict[markerStatus]
    else:
        errorFile.write('Invalid Marker Status (row %d): %s\n' % (lineNum, markerStatus))
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
    #		the Symbol is not an existing Official/Interim Marker
    #		the Symbol is not a Reserved Nomen Marker
    #
    #   if the Symbol is a Withdrawn Marker, then issue a warning
    #
    #	writes to the error file if the Symbol is a duplicate
    #
    # returns:
    #	0 if the Marker Symbol is not a duplicate
    #	1 if the Marker Symbol is a duplicate
    #
    '''

    #
    # warning if Symbol is Withdrawn
    #

    results = db.sql('''select _Marker_key from MRK_Marker 
        where _Organism_key = 1 
                and _Marker_Status_key in (2)
                and symbol = '%s'
        ''' % (symbol), 'auto')

    if len(results) > 0:
        errorFile.write('WARNING: Symbol is Withdrawn (row %d): %s\n\n' % (lineNum, symbol))

    #
    # official/reserved
    #

    results = db.sql('''
        select _Marker_key from MRK_Marker 
        where _Organism_key = 1 
                and _Marker_Status_key in (1,3)
                and symbol = '%s'
        ''' % (symbol), 'auto')

    if len(results) == 0:
        return 0
    else:
        errorFile.write('Symbol is Official/Reserved (row %d): %s\n' % (lineNum, symbol))
        return 1

def verifyChromosome(chromosome, lineNum):
    '''
    # requires:
    #	chromosome - the Chromosome
    #	lineNum - the line number of the record from the input file
    #
    # effects:
    #	verifies that:
    #		the Chromosome is valid
    #	writes to the error file if the Chromosome is invalid
    #
    # returns:
    #	1 if the Chromosome is valid
    #	0 if the Chromosome is invalid
    #
    '''

    results = db.sql('''select * from MRK_Chromosome where _Organism_key = 1 and chromosome = '%s'
        ''' % (chromosome), 'auto')

    if len(results) > 0:
        return 1
    else:
        errorFile.write('Invalid Chromosome (row %d): %s\n' % (lineNum, chromosome))
        return 0

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

    if logicalDB in logicalDBDict:
        logicalDBKey = logicalDBDict[logicalDB]
    else:
        errorFile.write('Invalid Logical DB (row %d): %s\n' % (lineNum, logicalDB))
        logicalDBKey = 0

    return(logicalDBKey)

def verifyMCVTerm(mcvTerm, lineNum):
    '''
    # requires:
    #	mcvTerm - the MCV Term
    #	lineNum - the line number of the record from the input file
    #
    # effects:
    #	verifies that:
    #		the MCV Term exists 
    #	writes to the error file if the MCV Term is invalid
    #
    # returns:
    #	0 if the MCV Term is invalid
    #	MCV Term Key if the MCV Term is valid
    #
    '''

    mcvTermKey = 0

    if mcvTerm in mcvDict:
        mcvTermKey = mcvDict[mcvTerm]
    else:
        errorFile.write('Invalid MCV Term (row %d): %s\n' % (lineNum, mcvTerm))
        mcvTermKey = 0

    return(mcvTermKey)

def sanityCheck(markerType, symbol, chromosome, markerStatus, jnum, synonyms, 
        otherAccIDs, createdBy, lineNum):
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

    global markerTypeKey
    global markerStatusKey
    global referenceKey
    global createdByKey
    global logicalDBKey
    global mcvTermKey
    global otherAccDict
    global mcvDict
    global markerLookup
    global referenceLookup

    error = 0

    markerTypeKey = loadlib.verifyMarkerType(markerType, lineNum, errorFile)
    markerStatusKey = verifyMarkerStatus(markerStatus, lineNum)
    referenceKey = loadlib.verifyReference(jnum, lineNum, errorFile)
    createdByKey = loadlib.verifyUser(createdBy, lineNum, errorFile)
    isDuplicateMarker = verifyDuplicateMarker(symbol, lineNum)
    chromosomeSearch = verifyChromosome(chromosome, lineNum)
    mcvTermKey = verifyMCVTerm(mcvTerm, lineNum)

    #
    # 1st instance will be loaded
    # duplicate rows in input file
    #
    if symbol in markerLookup:
        errorFile.write('WARNING: Duplicate Symbol in input file (row %d): %s\n' % (lineNum, symbol))
        error = 1
    else:
        markerLookup.append(symbol)

    #
    # Duplciate Reference
    #
    if len(referenceLookup) > 0 and referenceKey not in referenceLookup:
        errorFile.write('More than 1 Reference in input file (row %d): %s\n' % (lineNum, symbol))
        error = 1
    else:
        referenceLookup.append(referenceKey)

    #if len(synonyms) == 0:
        #errorFile.write('WARNING: Missing Synonyms (row %d): %s\n' % (lineNum, symbol))

    # 
    # Sequences
    # other acc ids
    #

    #if len(otherAccIDs) == 0:
        #errorFile.write('WARNING: Missing Sequences (row %d): %s\n' % (lineNum, symbol))

    for otherAcc in str.split(otherAccIDs, '|'):
        if len(otherAcc) > 0:
            try:
                [logicalDB, acc] = str.split(otherAcc, ':')
                logicalDBKey = verifyLogicalDB(logicalDB, lineNum)
                if logicalDBKey > 0:
                        otherAccDict[acc] = logicalDBKey
                else:
                        error = 1
            except:
                errorFile.write('Sequences without Logical DB (row %d): %s\n' % (lineNum, otherAcc))
                error = 1

    #
    # check if sequences are associated with other markers.
    # if so, send warning but allow load to continue
    #
    for acc in list(otherAccDict.keys()):
        results = db.sql('''select m.symbol 
                from MRK_Marker m, ACC_Accession a
                where m._Organism_key = 1 
                        and m._Marker_key = a._Object_key
                        and a.accID = '%s'
                        and a._MGIType_key = 2
                ''' % (acc), 'auto')

        for r in results:
                errorFile.write('WARNING: Sequence is associated with other Marker (row %d): %s ; %s\n\n' 
                        % (lineNum, acc, r['symbol']))

    #
    # invalid terms
    #

    if markerTypeKey == 0 or \
       markerStatusKey == 0 or \
       referenceKey == 0 or \
       isDuplicateMarker == 1 or \
       chromosomeSearch == 0 or \
       createdByKey == 0 or \
       mcvTermKey == 0:

        # set error flag to true
        error = 1

    return (error)

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

    global markerKey, accKey, mgiKey, synKey, alleleKey
    global noteKey, historyKey, mappingKey, mcvKey
    global refAssocKey

    results = db.sql(''' select nextval('mrk_marker_seq') as maxKey ''', 'auto')
    markerKey = results[0]['maxKey']

    results = db.sql(''' select nextval('mrk_history_seq') as maxKey ''', 'auto')
    historyKey = results[0]['maxKey']

    results = db.sql(''' select nextval('all_allele_seq') as maxKey ''', 'auto')
    alleleKey = results[0]['maxKey']

    results = db.sql(''' select nextval('mgi_note_seq') as maxKey ''', 'auto')
    noteKey = results[0]['maxKey']

    results = db.sql(''' select nextval('mgi_reference_assoc_seq') as maxKey ''', 'auto')
    refAssocKey = results[0]['maxKey']

    results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
    accKey = results[0]['maxKey']

    results = db.sql(''' select nextval('mgi_synonym_seq') as maxKey ''', 'auto')
    synKey = results[0]['maxKey']

    results = db.sql('select maxNumericPart + 1 as maxKey from ACC_AccessionMax where prefixPart = \'%s\'' % (mgiPrefix), 'auto')
    mgiKey = results[0]['maxKey']

    results = db.sql(''' select nextval('mld_expt_marker_seq') as maxKey ''', 'auto')
    mappingKey = results[0]['maxKey']

    results = db.sql(''' select nextval('voc_annot_seq') as maxKey ''', 'auto')
    mcvKey = results[0]['maxKey']

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

    global statusDict, logicalDBDict, mcvDict

    results = db.sql('select _Marker_Status_key, status from MRK_Status', 'auto')
    for r in results:
        statusDict[r['status']] = r['_Marker_Status_key']

    results = db.sql('select _LogicalDB_key, name from ACC_LogicalDB', 'auto')
    for r in results:
        logicalDBDict[r['name']] = r['_LogicalDB_key']

    results = db.sql('''
        select a.accid , t._term_key
        from ACC_Accession a, VOC_Term t
        where a._logicaldb_key = 146 
        and a._mgitype_key = 13 
        and a.preferred = 1
        and a._object_key = t._term_key
        ''', 'auto')
    for r in results:
        mcvDict[r['accid']] = r['_term_key']
    #print(mcvDict)

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

    global bcpon
    global markerKey, accKey, mgiKey, synKey, refAssocKey, createdByKey, alleleKey
    global noteKey, historyKey, mappingKey, mcvKey
    global markerType 
    global symbol 
    global name 
    global chromosome 
    global markerStatus 
    global jnum 
    global synonyms 
    global otherAccIDs 
    global mcvTerm
    global notes 
    global createdBy
    global otherAccDict
    global mcvDict
    global markerLookup
    global mgiCount

    # For each line in the input file

    lineNum = 0

    for line in inputFile.readlines():

        lineNum = lineNum + 1
        otherAccDict = {}

        # Split the line into tokens
        tokens = str.split(line[:-1], '\t')

        try:
            markerType = tokens[0]
            symbol = tokens[1]
            name = tokens[2]
            chromosome = tokens[3]
            markerStatus = tokens[4]
            jnum = tokens[5]
            synonyms = tokens[6]
            otherAccIDs = tokens[7]
            mcvTerm = tokens[8]
            notes = tokens[9]
            createdBy = tokens[10]
        except:
            errorFile.write('Invalid Line (missing column(s)) (row %d): %s\n' % (lineNum, line))
            continue

        #
        # sanity checks
        #

        if sanityCheck(markerType, symbol, chromosome, markerStatus, jnum, synonyms,
                otherAccIDs, createdBy, lineNum) == 1:
            errorFile.write(str(tokens) + '\n\n')

            # uncomment, if the bcp should not run if at least 1 error is found
            #bcpon = 0

            continue

        if chromosome == 'UN':
                cmOffset = -999
        else:
                cmOffset = -1

        # if no errors, process the marker
        markerFile.write('%d|1|%d|%d|%s|%s|%s||%s|%s|%s|%s|%s\n' \
            % (markerKey, markerStatusKey, markerTypeKey, symbol, name, chromosome, cmOffset, \
                createdByKey, createdByKey, cdate, cdate))

        mrkcurrentFile.write('%d|%d|%s|%s\n' \
            % (markerKey, markerKey, cdate, cdate))

        historyFile.write('%d|%d|106563604|106563610|%d|%d|1|%s|%s|%s|%s|%s|%s\n' \
            % (historyKey, markerKey, markerKey, referenceKey, name, cdate,
                createdByKey, createdByKey, cdate, cdate))

        # maybe we don't need this
        refFile.write('%d|%d|%d|%d|%d|%s|%s|%s|%s\n' \
            % (refAssocKey, referenceKey, markerKey, mgiTypeKey, \
                refAssocTypeKey, createdByKey, createdByKey, cdate, cdate))

        # MGI Accession ID for the marker

        accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s|%s\n' \
            % (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, markerKey, \
                mgiTypeKey, createdByKey, createdByKey, cdate, cdate))

        # Sequence Notes (1009)
        if len(notes) > 0:
            notes = notes.replace('|', '\\|')
            noteFile.write('%d|%s|2|1009|%s|%s|%s|%s|%s\n' \
                % (noteKey, markerKey, notes, createdByKey, createdByKey, cdate, cdate))
            noteKey = noteKey + 1

        # MCV Term (1011)
        mcvFile.write('%d|1011|%s|%s|1614158|%s|%s\n' \
            % (mcvKey, markerKey, mcvTermKey, cdate, cdate))
        mcvKey = mcvKey + 1

        # write record back out and include MGI Accession ID
        outputFile.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
                % (markerType, symbol, name, chromosome, \
                markerStatus, jnum, mgi_utils.prvalue(synonyms), \
                mgi_utils.prvalue(otherAccIDs), \
                mgi_utils.prvalue(mcvTerm), \
                mgi_utils.prvalue(notes), createdByKey, \
                mgiPrefix + str(mgiKey)))

        # mapping record; write it out before incrementing the acc id keys

        mappingFile.write('%s|%s%d|%s|%s|%s|%s|%s|%s|%s\n' \
            % (mappingKey, mgiPrefix, mgiKey, chromosome, mappingCol3, mappingCol4, \
                mappingCol5, mappingCol6, jnum, createdBy))

        accKey = accKey + 1
        mgiKey = mgiKey + 1
        refAssocKey = refAssocKey + 1
        mappingKey = mappingKey + 1
        mgiCount = mgiCount + 1

        # synonyms
        for o in str.split(synonyms, '|'):
            if len(o) > 0:
                synFile.write('%d|%d|%d|%d|%s|%s|%s|%s|%s|%s\n' \
                    % (synKey, markerKey, mgiTypeKey, synTypeKey, referenceKey, \
                        o, createdByKey, createdByKey, cdate, cdate))
                synKey = synKey + 1

        # accession ids

        for acc in list(otherAccDict.keys()):
            prefixpart, numericpart = accessionlib.split_accnum(acc)
            accFile.write('%d|%s|%s|%s|%d|%d|%d|0|1|%s|%s|%s|%s\n' \
                % (accKey, acc, prefixpart, numericpart, otherAccDict[acc], \
                    markerKey, mgiTypeKey, createdByKey, createdByKey, \
                    cdate, cdate))
            accrefFile.write('%d|%s|%s|%s|%s|%s\n' \
                % (accKey, referenceKey, createdByKey, createdByKey, \
                    cdate, cdate))
            accKey = accKey + 1

        #
        # if 'official' and markerType = 'gene'
        #

        if markerStatus == 'official' and markerTypeKey == 1:
            if symbol.find('mt-') < 0 or \
               name.find('withdrawn, =') < 0 or  \
               name.find('dna segment') < 0 or \
               name.find('EST ') < 0 or \
               name.find('expressed sequence') < 0 or \
               name.find('cDNA sequence') < 0 or \
               name.find('gene model') < 0 or \
               name.find('hypothetical protein') < 0 or \
               name.find('ecotropic viral integration site') < 0 or \
               name.find('viral polymerase') < 0:

                alleleFile.write('%d|%d|-2|847095|847131|847114|3982955|11025586|%s|%s|1|0|0||4268545|%s|%s|%s|%s|%s|%s\n' \
                        % (alleleKey, markerKey, symbol + '<+>', 'wild type', createdByKey, createdByKey, createdByKey, cdate, cdate, cdate))

                # MGI Accession ID for the allele
                accFile.write('%d|%s%d|%s|%s|1|%d|%d|0|1|%s|%s|%s|%s\n' \
                    % (accKey, mgiPrefix, mgiKey, mgiPrefix, mgiKey, alleleKey, \
                        alleleTypeKey, createdByKey, createdByKey, cdate, cdate))

                alleleKey = alleleKey + 1
                accKey = accKey + 1
                mgiKey = mgiKey + 1
                mgiCount = mgiCount + 1

        markerKey = markerKey + 1
        historyKey = historyKey + 1

    # end of "for line in inputFile.readlines():"

    markerFile.close()
    refFile.close()
    synFile.close()
    accFile.close()
    accrefFile.close()
    mappingFile.close()
    mrkcurrentFile.close()
    historyFile.close()
    alleleFile.close()
    noteFile.close()
    mcvFile.close()
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

    bcpCommand = os.environ['PG_DBUTILS'] + '/bin/bcpin.csh'
    currentDir = os.getcwd()

    bcp1 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MRK_Marker', currentDir, markerFileName)

    bcp2 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MGI_Reference_Assoc', currentDir, refFileName)

    bcp3 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MGI_Synonym', currentDir, synFileName)

    bcp4 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'ACC_Accession', currentDir, accFileName)

    bcp5 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'ACC_AccessionReference', currentDir, accrefFileName)

    bcp6 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MRK_Current', currentDir, mrkcurrentFileName)

    bcp7 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MRK_History', currentDir, historyFileName)

    bcp8 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'ALL_Allele', currentDir, alleleFileName)

    bcp9 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'MGI_Note', currentDir, noteFileName)

    bcp10 = '%s %s %s %s %s %s "|" "\\n" mgd' % \
        (bcpCommand, db.get_sqlServer(), db.get_sqlDatabase(), 'VOC_Annot', currentDir, mcvFileName)

    diagFile.write('%s\n' % bcp1)
    diagFile.write('%s\n' % bcp2)
    diagFile.write('%s\n' % bcp3)
    diagFile.write('%s\n' % bcp4)
    diagFile.write('%s\n' % bcp5)
    diagFile.write('%s\n' % bcp6)
    diagFile.write('%s\n' % bcp7)
    diagFile.write('%s\n' % bcp8)
    diagFile.write('%s\n' % bcp9)
    diagFile.write('%s\n' % bcp10)

    os.system(bcp1)
    os.system(bcp2)
    os.system(bcp3)
    os.system(bcp4)
    os.system(bcp5)
    os.system(bcp6)
    os.system(bcp7)
    os.system(bcp8)
    os.system(bcp9)
    os.system(bcp10)

    # update the max accession ID value
    db.sql('select * from ACC_setMax (%d)' % (mgiCount), None)
    db.commit()

    # update mrk_marker_seq auto-sequence
    db.sql(''' select setval('mrk_marker_seq', (select max(_Marker_key) from MRK_Marker)) ''', None)
    db.commit()

    # update mgi_note_seq auto-sequence
    db.sql(''' select setval('mgi_note_seq', (select max(_Note_key) from MGI_Note)) ''', None)
    db.commit()
    
    # update mrk_history_seq auto-sequence
    db.sql(''' select setval('mrk_history_seq', (select max(_Assoc_key) from MRK_History)) ''', None)
    db.commit()

    # update mgi_reference_assoc_seq auto-sequence
    db.sql(''' select setval('mgi_reference_assoc_seq', (select max(_Assoc_key) from MGI_Reference_Assoc)) ''', None)
    db.commit()

    # update mgi_synonym_seq auto-sequence
    db.sql(''' select setval('mgi_synonym_seq', (select max(_Synonym_key) from MGI_Synonym)) ''', None)
    db.commit()

    # update all_allele_seq auto-sequence
    db.sql(''' select setval('all_allele_seq', (select max(_Allele_key) from ALL_Allele)) ''', None)
    db.commit()

    # update mld_expt_marker_seq auto-sequence
    db.sql(''' select setval('mld_expt_marker_seq', (select max(_Assoc_key) from MLD_Expt_Marker)) ''', None)
    db.commit()

    # update voc_annot_seq auto-sequence
    db.sql(''' select setval('voc_annot_seq', (select max(_Annot_key) from VOC_Annot)) ''', None)
    db.commit()
    
#
# Main
#

#print 'verifyMode()'
verifyMode()

#print 'init()'
init()

#print 'setPrimaryKeys()'
setPrimaryKeys()

#print 'loadDictionaries()'
loadDictionaries()

#print 'processFile()'
processFile()

if not DEBUG and bcpon:
    print('sanity check PASSED : loading data')
#    print('bcpFiles()')
    bcpFiles()
    exit(0)
else:
    exit(1)

