from flask import Flask, render_template, request, jsonify, send_from_directory
from threading import Timer
import pdb
import re
import threading, time, os
from . import myLogger

# Can use this for the sunset time: https://en.wikipedia.org/wiki/Sunrise_equation

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html

app = Flask(__name__)

class Server(object):
    allowControl = 0  # Allow or disallow control of temp
    alwaysAllow = 0  # Ignore flag above.
    logFileName = ''

    def  __init__(self,logFileName='logFile.log'):
        # This is so self.offTimer exists!
        self.logFileName = logFileName
        myLogger.setLogger(logFileName)
    
    def favicon(self):
        return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
        
    # return index page when IP address of RPi is typed in the browser
    def Index(self,pageFile='index.html'):
        return render_template(pageFile)
    
    def reboot(self):
        os.system('sudo reboot now')

    def kg(self):
        os.system('sudo killall -SIGHUP gunicorn')
        
    def getLog(self,numLines=0):
        with open(self.logFileName) as f:
            allLines = f.readlines()
            allLines.reverse()
            if numLines: allLines = allLines[0:numLines]
        return ''.join(allLines)
            
        
    def GetUptime(self):
        # get uptime from the linux terminal command
        from subprocess import check_output
        uptime = check_output(["uptime"])
        uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime)
        return uptime

@app.route('/favicon.ico')
def favicon():
    return server.favicon()
            
@app.route("/reboot")
def reboot():
    server.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    server.kg()
    return ('', 204)


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return server.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)
    

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
