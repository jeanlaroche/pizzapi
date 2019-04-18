from picamera import PiCamera
from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.baseServer import Server
from BaseClasses.utils import myTimer
from BaseClasses import myLogger
import pdb
import pigpio
import logging
import time
from threading import Timer
import threading
import BaseClasses.utils as utils
import glob
import re
#https://picamera.readthedocs.io/en/release-1.13/
# Insert an image using javascript:
# https://www.quora.com/How-do-you-insert-an-image-in-Javascript

app = Flask(__name__)

class cameraServer(Server):
    fileNumber = 0
    
    def  __init__(self):
        myLogger.setLogger('camera.log',level=logging.INFO)
        self.camera = PiCamera()
        self.camera.start_preview()
        allImages = glob.glob('static/image*.jpg')
        allNums = re.findall('image_(\d\d\d)',' '.join(allImages))
        allNums = [int(item) for item in allNums]
        self.fileNumber = max(allNums)+1 if len(allNums) else 0
        logging.info("Starting camera server, next file num: %d",self.fileNumber)
    
    def __del__(self):
        self.camera.stop_preview()
        
    def snap(self):
        thisTime = time.strftime("%a_%d_%m_%Hh%Mm%S",time.localtime())
        outFile = "static/image_{:03d}_{}.jpg".format(self.fileNumber,thisTime)
        logging.info("Taking snapshot: %s",outFile)
        self.camera.capture(outFile)
        self.fileNumber += 1
        return jsonify(data='Took a pic, saved in {}'.format(outFile))

    def getLog(self):
        with open('camera.log') as f:
            allLines = f.readlines()
            allLines = list(reversed(allLines))
            return jsonify(log = ''.join(allLines[0:100]))
            
    def getData(self):
        uptime = self.GetUptime()
        return jsonify(data = 'Nothing to report', uptime=uptime)
        
cs = cameraServer()

@app.route('/Camera/favicon.ico')
def favicon():
    return cs.favicon()

@app.route('/Camera/snap')
def snap():
    return cs.snap()
    
@app.route('/Camera/getData')
def getData():
    return cs.getData()

@app.route('/Camera/getLog')
def getLog():
    return cs.getLog()


# return index page when IP address of RPi is typed in the browser
@app.route("/Camera/")
@app.route("/")
def Index():
    return cs.Index()
    
    

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False) #< for use with gunicorn, point browser to IP:8080