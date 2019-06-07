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
        logging.info("PWM Frequency %d",self.pi.get_PWM_frequency(outGPIO))

        self.counter = 0
        
        YL_40=0x48
        self.handle = self.pi.i2c_open(1, YL_40, 0)
        self.loadParams()
        self.loop()
        
    def __delete__(self):
        print "DELETE"
        self.pi.stop()

    def readADInputs(self):
        self.counter = (self.counter + 1) % 10
        # Somehow input 1 does not seem to work any longer?
        inputs=[0,2]
        for a in range(0,2):
            # Massaging: get the mean of 512 values, then use the 1024 last one for the feedback and many more for the display
            values = readValues(chan=a,gain=self.gains[a],numVals=100,verbose=0)[0]
            meanVal = 1.*np.mean(values)/self.factors[self.gains[a]]
            self.outputVHist[a] = np.roll(self.outputVHist[a],1)
            self.outputVHist[a][0]= meanVal
            self.outputV[a]=np.mean(self.outputVHist[a][0:self.nMean])
            self.outputVSmooth[a] = np.mean(self.outputVHist[a])
    
    def loop(self):
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
        
        
    def regulateForTargetV(self):
        fullRange = 2048.
        
        def regLoop():
            ratio,ratioV,ratioA = 0,0,0
            control = 'V'
            while 1:
                self.readADInputs()
                try:
                    socketio.emit('currentValues', {'data': str,'VOut':VOut,'AOut':AOut,'VMax':VMax,'AMax':AMax,'Control':control,
                        'PowerOn':self.PowerOn,'Power':Power,'mWHour':self.mWHour})
                except:
                    pass
        t = threading.Thread(target=regLoop)
        t.daemon = True
        t.start()
        
    def calibrate(self,AorV):
        logging.info("Calibrating %s",AorV)
        
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'targetA':self.targetOutA,'targetV':self.targetOutV,'dacToVolt':self.dacToVolt,'dacToAmp':self.dacToAmp,
            'mWHour':self.mWHour},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.targetOutA = D['targetA']
                self.targetOutV = D['targetV']
                self.dacToVolt = D['dacToVolt']
                self.dacToAmp = D['dacToAmp']
                self.mWHour = D['mWHour']
        except:
            pass
        


@app.route('/favicon.ico')
def favicon():
    return zapper.favicon()
            
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
    return(jsonify(VOut=zapper.targetOutV/zapper.posToAdcV,AOut=zapper.targetOutA/zapper.posToAdcA))

@app.route('/setRatio_<int:param1>')
def setRatio(param1):
    zapper.targetOutV = param1/100.*256
    return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return zapper.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)

@socketio.on('setTargetV')
def setTargetV(arg1):
    zapper.targetOutV = int(arg1['data']*zapper.posToAdcV)
    zapper.saveParams()

@socketio.on('setTargetA')
def setTargetA(arg1):
    zapper.targetOutA = int(arg1['data']*zapper.posToAdcA)
    zapper.saveParams()

@socketio.on('TurnOnOff')
def turnOnOff(arg1):
    print "TURNING ON?OFF {}".format(arg1['data'])
    val = int(arg1['data'])
    if val in [0,1]: zapper.turnOn(val)
    else: zapper.resetMwHour()

@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    zapper.calibrate(arg1['data'])

    
zapper = Zapper()

if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    #zapper.glow()
    # try:
    socketio.run(app,host='0.0.0.0',port=8080)
        # app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
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
    
    