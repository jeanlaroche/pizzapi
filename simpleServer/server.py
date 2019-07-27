import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging, json
from BaseClasses import myLogger
from BaseClasses.utils import *
import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

relayGPIO = 10

class MainServer(Server):
    
    paramFile = 'params.json'
    
    def __init__(self):
        myLogger.setLogger('server.log',mode='a',dateFormat="%H:%M:%S",level=logging.WARNING)
        self.logFileName = 'server.log'
        logging.warning('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(relayGPIO, pigpio.OUTPUT)
        self.pi.write(relayGPIO,0)
                       
    def __delete__(self):
        print "DELETE"
        self.pi.stop()
        
    def watchForGopher(self):
        
        def sendData(str):
            try:
                socketio.emit('currentValues', {'status': str,'curV':self.curV,'calibV':self.calibV,'lastTripped':self.lastTripTime,
                'time':'Current time: ' + time.ctime(time.time()),'threshV':self.threshFactor*self.calibV,'zapTimeS':self.zapTimeS})
            except:
                pass
        
        def doLoop():
            while 1:
                #self.readADInputs()
                values = readValues(chan=0,gain=self.gain,numVals=100,verbose=0)[0]
                meanVal = 1.*np.mean(values)*self.scale*self.maxVolts[self.gain]
                #print "val {}".format(meanVal)
                if self.status == status_waiting: str = 'Status: waiting... '
                if self.status == status_tripped: str = 'Status: tripped... '
                if self.status == status_off: str = 'Status: off... '
                self.curV = meanVal
                sendData(str)
                if self.curV < self.calibV * self.threshFactor and self.status == status_waiting:
                    # Turn the relay on
                    logging.warning('ZAP! Triggering relay. V = %.2f Threshold = %.2f',self.curV,self.calibV * self.threshFactor)
                    self.status = status_tripped
                    self.pi.write(relayGPIO,1)
                    sendData('Triggering relay')
                    self.lastTripTime = 'Last zapped: {}'.format(time.asctime(time.localtime()))
                    # Since we're on only for a little while, we can just sleep here, then reset the relay
                    time.sleep(self.zapTimeS)
                    self.pi.write(relayGPIO,0)
                    
                time.sleep(.1)
        t = threading.Thread(target=doLoop)
        t.daemon = True
        t.start()
                
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            pass
#            json.dump({'calibV':self.calibV, 'gain':self.gain, 'threshFactor':self.threshFactor,'zapTimeS':self.zapTimeS},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
        except:
            pass
        


@app.route('/favicon.ico')
def favicon():
    print "FAV ICON"
    return ('', 204)
            
@app.route("/reboot")
def reboot():
    server.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    server.kg()
    return ('', 204)

@app.route('/_init')
def init():
    print "INIT"
    #return(jsonify(threshFactor=server.threshFactor,zapTimeS=server.zapTimeS, log=server.getLog(400)))

# @app.route('/setRatio_<int:param1>')
# def setRatio(param1):
    # server.targetOutV = param1/100.*256
    # return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    print "/"
    return server.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)


@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    #server.calibrate()

@app.route('/log')
def log():
    print "LOG"
    return jsonify(log=server.getLog())

    
server = MainServer()

if __name__ == "__main__":
    socketio.run(app,host='0.0.0.0',port=8080)
    exit(0)
    