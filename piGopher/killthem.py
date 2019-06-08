import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging, json
from BaseClasses import myLogger
import numpy as np
from readADS1015 import *

relayGPIO = 18      # GPIO used to control the relay

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

status_waiting       = 0
status_tripped       = 1
status_off       = 2

class Zapper(Server):
    
    paramFile = 'params.json'
    
    def __init__(self):
        myLogger.setLogger('zapper.log',mode='a',dateFormat="%H:%M:%S",level=logging.WARNING)
        self.logFileName = 'zapper.log'
        logging.warning('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(relayGPIO, pigpio.OUTPUT)
        self.pi.write(relayGPIO,0)
        
        # The gain of the selectable gain in the AD converter. Between 0 and 5.
        self.gain = 0
        # Max input voltage for each gain value.
        self.maxVolts = [6.144,4.096,2.048,1.024,0.512,0.256]
        # The output voltage is a 12 bit signed integer.
        self.scale = np.power(2.,-11)
        # Calibration voltage (voltage when nobody touches the probe)
        self.calibV = 0
        # Current measured voltage.
        self.curV = 0
        # self.threshFactor * self.calibV is the threshold below which we trigger the relay
        self.threshFactor = .9 
        # The relay is on for this amount of time.
        self.zapTimeS = 4
        # Status. 
        self.status = status_off
        # Last time tripped
        self.lastTripTime = ''
        
        YL_40=0x48
        self.handle = self.pi.i2c_open(1, YL_40, 0)
        self.loadParams()
        #self.testLoop()
        self.watchForGopher()
        
    def __delete__(self):
        print "DELETE"
        self.pi.stop()

    # def readADInputs(self):
        # self.counter = (self.counter + 1) % 10
        # # Somehow input 1 does not seem to work any longer?
        # inputs=[0,2]
        # for a in range(0,2):
            # # Massaging: get the mean of 512 values, then use the 1024 last one for the feedback and many more for the display
            # values = readValues(chan=a,gain=self.gain,numVals=100,verbose=0)[0]
            # meanVal = 1.*np.mean(values)*self.maxVolts[self.gain]
            # self.outputVHist[a] = np.roll(self.outputVHist[a],1)
            # self.outputVHist[a][0]= meanVal
            # self.outputV[a]=np.mean(self.outputVHist[a][0:self.nMean])
            # self.outputVSmooth[a] = np.mean(self.outputVHist[a])
    
    def testLoop(self):
        def doLoop():
            cnt = 0
            cntOn = 0
            chan = 0
            gain = 1
            maxVal=0
            minVal=10000
            pi.i2c_write_device(h, [0x01, 0xC0+(chan<<4)+(gain<<1), 0x83])
            pi.i2c_write_device(h, [0x00])
            while 1:
                cnt += 1
                num_read, data = pi.i2c_read_device(h, 2)
                value = (unpack('>h',data[0:2])[0])>>4
                #print "val {}".format(value)
        t = threading.Thread(target=doLoop)
        t.daemon = True
        t.start()
        
        
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
        
    def calibrate(self):
        logging.warning("Calibrating")
        self.calibV = self.curV
        self.saveParams()
    
    def reArm(self):
        logging.warning("Resetting, re-arming, curV %.2f calibV %.2f",self.curV,self.calibV)
        self.status = status_waiting
    
    def turnOn(self,onOff):
        if onOff:
            if self.status == status_off: 
                self.status = status_waiting
        else:
            self.status = status_off
        
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'calibV':self.calibV, 'gain':self.gain, 'threshFactor':self.threshFactor,'zapTimeS':self.zapTimeS},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.calibV = D['calibV']
                self.gain = D['gain']
                self.threshFactor = D['threshFactor']
                self.zapTimeS = D['zapTimeS']
        except:
            pass
        


@app.route('/favicon.ico')
def favicon():
    print "FAV ICON"
    return ('', 204)
            
@app.route("/reboot")
def reboot():
    zapper.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    zapper.kg()
    return ('', 204)

@app.route('/_init')
def init():
    print "INIT"
    return(jsonify(threshFactor=zapper.threshFactor,zapTimeS=zapper.zapTimeS))

@app.route('/setRatio_<int:param1>')
def setRatio(param1):
    zapper.targetOutV = param1/100.*256
    return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    print "/"
    return zapper.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)

@socketio.on('setOffset')
def setOffset(arg1):
    zapper.threshFactor = float(arg1['data'])/100
    zapper.saveParams()

@socketio.on('setZapTimeS')
def setZapTimeS(arg1):
    zapper.zapTimeS = float(arg1['data'])/10
    zapper.saveParams()

@socketio.on('reArm')
def reArm():
    zapper.reArm()

@socketio.on('TurnOnOff')
def turnOnOff(arg1):
    print "TURNING ON?OFF {}".format(arg1['data'])
    val = int(arg1['data'])
    zapper.turnOn(val)

@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    zapper.calibrate()

@app.route('/log')
def log():
    print "LOG"
    return jsonify(log=zapper.getLog())

    
zapper = Zapper()

if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    #zapper.glow()
    # try:
    socketio.run(app,host='0.0.0.0',port=8080)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    # except:
        # print "STOP"
        # zapper.pi.stop()
    exit(0)

    # while 1:
        # a = raw_input('Command ->[]')
        # a = int(a)
        # lc.turnLigthOnOff(abs(a),a>0)

    #zapper.setDutyCycle(1)
    while 1:
        a=raw_input('duty->')
        ratio = float(a)
        zapper.setDutyCycle(ratio)
    
    