import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging, json
from BaseClasses import myLogger
import numpy as np
from readADS1015 import *

outGPIO = 18

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


class Zapper(Server):
    
    paramFile = 'params.json'
    
    def __init__(self):
        myLogger.setLogger('zapper.log',mode='a',dateFormat="%H:%M:%S")
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(outGPIO, pigpio.OUTPUT)
        self.counter = 0
        self.gain = 2
        self.Vots = [6.144,4.096,2.048,1.024,0.512,0.256]
        self.scale = np.power(2.,-11)
        self.calibV = 0
        self.curV = 0
        
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
            # meanVal = 1.*np.mean(values)*self.Vots[self.gain]
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
                print "val {}".format(value)
        t = threading.Thread(target=doLoop)
        t.daemon = True
        t.start()
        
        
    def watchForGopher(self):
        fullRange = 2048.
        
        def doLoop():
            while 1:
                #self.readADInputs()
                values = readValues(chan=0,gain=self.gain,numVals=10,verbose=0)[0]
                meanVal = 1.*np.mean(values)*self.scale*self.Vots[self.gain]
                print "val {}".format(meanVal)
                str = 'Nothing'
                self.curV = meanVal
                AOut = 0
                VMax = 0
                AMax = 0
                control = 0
                try:
                    socketio.emit('currentValues', {'data': str,'curV':self.curV,'calibV':self.calibV,'VMax':VMax,'AMax':AMax,'Control':control})
                except:
                    pass
                time.sleep(.3)
        t = threading.Thread(target=doLoop)
        t.daemon = True
        t.start()
        
    def calibrate(self):
        logging.info("Calibrating")
        self.calibV = self.curV
        
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'calibV':self.calibV},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.calibV = D['calibV']
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
    return(jsonify(gain=zapper.gain))

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

@socketio.on('setGain')
def setGain(arg1):
    zapper.gain = int(arg1['data']/25)
    #print "SET GAIN {}".format(zapper.gain)
    zapper.saveParams()

@socketio.on('setTargetA')
def setTargetA(arg1):
    #zapper.targetOutA = int(arg1['data']*zapper.posToAdcA)
    zapper.saveParams()

@socketio.on('TurnOnOff')
def turnOnOff(arg1):
    print "TURNING ON?OFF {}".format(arg1['data'])
    val = int(arg1['data'])
    #if val in [0,1]: zapper.turnOn(val)
    #else: zapper.resetMwHour()

@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    zapper.calibrate()

    
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
    
    