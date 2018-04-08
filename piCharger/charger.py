import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger
import numpy as np

outGPIO = 18

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


class Charger(Server):
    
    oscFreqHz = 320*4
    pwmRange = 1024
    target = 255
    def __init__(self):
        myLogger.setLogger('charger.log',mode='a')
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(outGPIO, pigpio.OUTPUT)
        self.pi.set_pull_up_down(outGPIO, pigpio.PUD_UP)
        self.pi.set_PWM_frequency(outGPIO,self.oscFreqHz)
        self.pi.set_PWM_range(outGPIO,self.pwmRange)
        self.pi.set_PWM_dutycycle(outGPIO,128)
        self.counter = 0
        #self.pi.write(outGPIO,1)
        
        YL_40=0x48
        self.handle = self.pi.i2c_open(1, YL_40, 0)
        self.aout = 0
        self.outputV = [0]*2
        self.outputVSmooth = [0]*2
        self.outputVHist = [256*np.ones(8)]*2
        self.nMean = 2
        self.regulateForTargetV()
        #self.glow()

    def readADInputs(self):
        for a in range(0,2):
            # self.aout = self.aout + 1
            try:
                self.pi.i2c_write_byte_data(self.handle, 0x40 | a, self.aout&0xFF)
            except:
                print "Write failed"
                continue
            if 0:
                v = self.pi.i2c_read_byte(self.handle)
                self.outputV = int(v)
            else:
                self.counter = (self.counter + 1) % 10
                n,bytes = self.pi.i2c_read_device(self.handle,512)
                meanVal = 1.*np.mean(bytes)
                self.outputVHist[a] = np.roll(self.outputVHist[a],1)
                self.outputVHist[a][0]= meanVal
                self.outputV[a]=np.mean(self.outputVHist[a][0:self.nMean])
                self.outputVSmooth[a] = np.mean(self.outputVHist[a])
        back = '\b'*16
        # back = '\n'
        
        
    def regulateForTargetV(self):
        self.target = 60
        fullRange = 256.
        self.setDutyCycle(1)
        def regLoop():
            ratio = 1
            maxStep = .2
            fork = 2
            while 1:
                self.readADInputs()
                step=0
                absDiff = abs(self.target-self.outputV[0])
                if absDiff > 15:
                    ratio += 1 * (self.target-self.outputV[0]) / fullRange
                elif absDiff > 2:
                    ratio += .3 * (self.target-self.outputV[0]) / fullRange
                ratio = max(0,min(ratio,1))
                self.setDutyCycle(ratio)
                # self.setDutyCycle(self.target/256.)
                time.sleep(0.0001)
                str = "input {:.1f} {:.1f} target {:.2f} ratio {:.0f} -- {}   ".format(self.outputV[0],self.outputV[1], self.target, ratio*self.pwmRange, self.counter)
                back = '\b'*(len(str)+1)
                print str+back,
                VOut = self.outputVSmooth[0] * 14.99/224.7
                socketio.emit('currentValues', {'data': str,'VOut':VOut})
        t = threading.Thread(target=regLoop)
        t.daemon = True
        t.start()

    def setDutyCycle(self,ratio):
        self.pi.set_PWM_dutycycle(outGPIO,int(self.pwmRange*(ratio)))
        
    def glow(self):
        def doGlow():
            while 1:
                for a in range(0,512):
                    if a>=256: a = 511-a
                    self.setDutyCycle(a/256.)
                    #print('{:.2f}'.format(a/256.))
                    time.sleep(0.002)
        t = threading.Thread(target=doGlow)
        t.daemon = True
        t.start()



@app.route('/favicon.ico')
def favicon():
    return charger.favicon()
            
@app.route("/reboot")
def reboot():
    charger.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    charger.kg()
    return ('', 204)

@app.route('/setRatio_<int:param1>')
def setRatio(param1):
    # print "SET RATIO {}".format(param1)
    #charger.setDutyCycle(param1/100.)
    charger.target = param1/100.*256
    return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return charger.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)

@socketio.on('my event')
def handle_my_custom_event(arg1):
    #print('received args:')
    # print arg1['data']
    charger.target = int(arg1['data']/100.*256)
    #emit('targetVal', {'data': charger.target})

    
charger = Charger()

if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    #charger.glow()
    socketio.run(app,host='0.0.0.0',port=8080)
    # app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    exit(0)

    # while 1:
        # a = raw_input('Command ->[]')
        # a = int(a)
        # lc.turnLigthOnOff(abs(a),a>0)

    #charger.setDutyCycle(1)
    while 1:
        a=raw_input('duty->')
        ratio = float(a)
        charger.setDutyCycle(ratio)
    
    