#!/usr/bin/python

###############################################
# Tabletalk
# An experiment by Rory Petty
# 7/19/2011
###############################################

# Dependencies
# python: simplejson,pycurl
# pygame - http://f0o.com/~rene/stuff/pygame-1.9.2pre-py2.6-macosx10.6.mpkg.zip
# binaries: sox

# Known Issues
# 1. sox/rec would like to record at 44.1 kHz and other nice numbers, but the google speech API maxes at 44000. We can decrease
#	the sampling rate but that might come at a cost of audio quality. Also, we're uploading 44.1 audio as 44.0, which could be
#	effecting our transcription quality
# 2. probably need a better solution than just polling the recordings dir for new files
# 3. switch to pexpect to better kill subprocesses spawned by sox/rec
# 4. better packaging of dependent python modules
# 5. use queue module?


import sys
#sys.path.append('/Library/Python/2.6/site-packages')
sys.path.append("/Users/rory/Dropbox/dev/TableTalk/PyTagCloud/src/")
import os
import time
import subprocess
import logging
import simplejson
import urllib
import urllib2
import pycurl
import signal
from StringIO import StringIO
#import pexpect

SOXDIR = "sox-14.3.2"
REC = "recordings"
BR = "44100"
UPLOADED = "uploaded"
GOOG_SPEECH_URL='https://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=en-US'
YAHOO_APP_ID = 'YahooDemo' # Change this to your API key
YAHOO_TE_URL_BASE = 'http://search.yahooapis.com/ContentAnalysisService/V1/termExtraction'

TE_PHRASES_FILE = "tabletalk_te_phrases.txt"


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

global te_file

class YahooSearchError(Exception):
	pass

def main():
	try:
		signal.signal(signal.SIGINT, signal_handler) #register signal handler to catch ctrl-c program exit
		
		if not os.path.exists(REC):
			os.makedirs(REC)
	
		if not os.path.exists(UPLOADED):
			os.makedirs(UPLOADED)

		# clear out previous recordings
		deleteDirContents(REC)
		deleteDirContents(UPLOADED)
	
		# start sox
		rec = subprocess.Popen(SOXDIR+"/rec -r "+BR+" "+REC+"/tabletalk.flac trim 0 00:00:10 : newfile : restart &> recording.log", shell=True)
		
		#blank the file each time
		te_file = open(TE_PHRASES_FILE,"w")
		te_file.close()


		while True:
			files = sorted([f for f in os.listdir(REC) 
				if os.path.isfile( os.path.join(REC, f) )])

			if files:
				#logging.info(files)
				
				body = StringIO()
				c = pycurl.Curl()
				c.setopt(c.POST, 1)
				c.setopt(c.URL, GOOG_SPEECH_URL)
				c.setopt(c.HTTPHEADER, ["Content-Type: audio/x-flac; rate=44000"])
				c.setopt(c.HTTPPOST, [("myfile", (c.FORM_FILE, os.path.join(REC,files[0])))])
				c.setopt(c.WRITEFUNCTION, body.write)
				
				try:
					c.perform()
				except pycurl.error, e:
					logging.info("Error: " + e)
					
				http_code = c.getinfo(c.HTTP_CODE)
				if http_code == 200:

					
					body.seek(0)				
					ret = simplejson.loads(body.read())
					
					#print "ret"
					#print ret
					#print "+++++++++++++++++"
					hypotheses = ret['hypotheses']
					#print hypotheses

					print "+++++++++++++++++"
					if len(hypotheses) > 0:
						transcription = hypotheses[0]['utterance']
						confidence = hypotheses[0]['confidence']
						print "Google Speech API:"
						print "Transcription: " + transcription
						print "Confidence: " + str(confidence)

						# send to yahoo term extraction api
						try:
							yte_ret = yahoo_term_extraction(transcription)
							print "Results from Yahoo Term Extraction API:"
							print yte_ret
							with open(TE_PHRASES_FILE, "a") as f:
								for s in yte_ret['Result']:
									f.write(s + '\n')
							f.close()
							
							#logging.info("Moving " + files[0] + " to uploaded dir")
							os.rename(os.path.join(REC,files[0]), os.path.join(UPLOADED,files[0]))
						except YahooSearchError, e:
						    print "An API error occurred."
						except IOError:
						    print "A network IO error occured during the call to the Yahoo Term Extraction API."

					
				else:	
					logging.info("ERROR: http request failed")
					
				c.close()
				time.sleep(0.02)
				print ""
				print ""
			else:
				time.sleep(1) # keeps cpu from going to 100% when no files to process (tight while loop)
	except KeyboardInterrupt:
		os.kill(rec.pid, signal.SIGTERM)		

def yahoo_term_extraction(context, query="", **kwargs):
    kwargs.update({
        'appid': YAHOO_APP_ID,
        'context': context, #for the Yahoo TE API, context is the required string to search. query allows you to provide optional terms
        'query': query,
        'output': 'json'
    })
    url = YAHOO_TE_URL_BASE + '?' + urllib.urlencode(kwargs)
    result = simplejson.load(urllib.urlopen(url))
    if 'Error' in result:
        # An error occurred; raise an exception
        raise YahooSearchError, result['Error']
    return result['ResultSet']

			
def call_command(command):
	process = subprocess.Popen(command.split(' '),
								stdout=subprocess.PIPE,
								stderr=subprocess.PIPE)
	return process.communicate()

def deleteDirContents(path):
	for the_file in os.listdir(path):
	    file_path = os.path.join(path, the_file)
	    try:
	        if os.path.isfile(file_path):
	            os.unlink(file_path)
	    except Exception, e:
	        print e

def signal_handler(signal, frame):
	print 'You pressed Ctrl+C'
	cleanup()
	sys.exit(0)

def cleanup():
	print "Exiting program"

if __name__ == "__main__":
    main()