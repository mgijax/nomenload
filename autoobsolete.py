#!/bin/csh -f -x

#
# Configuration file for auto-obsolete merges
#

if ( ${?MGICONFIG} == 0 ) then
	setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

setenv TODAY		`date +%m%d%Y`

setenv DATADIR  	/data/loads/mgi/autoobsolete
setenv INPUTFILE	${DATADIR}/autoobsolete.build36.2
setenv REFKEY		82823
#J:81858
setenv EVENTKEY 	6
setenv EVENTREASONKEY	6
setenv ADDASSYNONYM	0

setenv EI               ${EI_USRLOCALMGI}/ei
setenv EIUTILS          ${EI}/utilities
setenv NOMENBATCH       ${EIUTILS}/batchWithdrawal.py

