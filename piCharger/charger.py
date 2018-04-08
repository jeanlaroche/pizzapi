import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging, json
from BaseClasses import myLogger
import numpy as np

outGPIO = 18

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


class Charger(Server):
    
    oscFreqHz = 320*4
    pwmRange = 1024
    targetOutV = 255
    paramFile = 'params.json'
    def __init__(self):
        myLogger.setLogger('charger.log',mode='a')
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(outGPIO, pigpio.OUTPUT)
        # self.pi.set_pull_up_down(outGPIO, pigpio.PUD_UP)
        self.pi.set_PWM_frequency(outGPIO,self.oscFreqHz)
        self.pi.set_PWM_range(outGPIO,self.pwmRange)
        self.pi.set_PWM_dutycycle(outGPIO,0)
        self.counter = 0
        #self.pi.write(outGPIO,1)
        
        YL_40=0x48
        self.handle = self.pi.i2c_open(1, YL_40, 0)
        self.aout = 0
        self.outputV = [0]*2
        self.outputVSmooth = [0]*2
        self.outputVHist = [256*np.ones(8)]*2
        self.nMean = 2
        self.targetOutV = 0
        self.targetOutA = 5
        self.PowerOn = 1
        self.loadParams()
        self.regulateForTargetV()
        #self.glow()

    def readADInputs(self):
        self.counter = (self.counter + 1) % 10
        # Somehow input 1 does not seem to work any longer?
        inputs=[0,2]
        for a in range(0,2):
            try:
                self.pi.i2c_write_byte_data(self.handle, 0x00 | inputs[a], 0)
            except:
                print "Write failed"
                return
            # Massaging: get the mean of 512 values, then use the 1024 last one for the feedback and many more for the diaplsy
            n,bytes = self.pi.i2c_read_device(self.handle,512)
            meanVal = 1.*np.mean(bytes)
            self.outputVHist[a] = np.roll(self.outputVHist[a],1)
            self.outputVHist[a][0]= meanVal
            self.outputV[a]=np.mean(self.outputVHist[a][0:self.nMean])
            self.outputVSmooth[a] = np.mean(self.outputVHist[a])
        
    def regulateForTargetV(self):
        fullRange = 256.
        self.setDutyCycle(1)
        
        def controlFun(ratio,delta,mult=1,deadZone=2):
            # Simple feedback function.
            absDiff = abs(delta)
            if absDiff > 15:
                ratio += 1 * (delta) / fullRange * mult
            elif absDiff > deadZone:
                ratio += .3 * (delta) / fullRange * mult
            return max(0,min(ratio,1))        
        
        def regLoop():
            ratio,ratioV,ratioA = 0,0,0
            control = 'V'
            while 1:
                self.readADInputs()
                if self.PowerOn:
                    # Update the two ratios according to desired V and A
                    delta = self.targetOutV-self.outputV[0]
                    ratioV = controlFun(ratioV,delta)
                    delta = self.targetOutA-self.outputV[1]
                    ratioA = controlFun(ratioA,delta,mult=10,deadZone=0)
                    # But pick the minimum of the two.
                    ratio,control = min(ratioV,ratioA),'V' if ratioV < ratioA else 'A'
                    ratioA,ratioV=ratio,ratio
                    self.setDutyCycle(ratio)
                else:
                    self.setDutyCycle(0)
                time.sleep(0.0001)
                str = "{:.1f}V {:.1f}A tarV {:.2f} tarA {:.2f} ratio {:.0f}({}) -- {}   ".format(self.outputV[0],self.outputV[1], self.targetOutV, self.targetOutA, ratio*self.pwmRange, control, self.counter)
                back = '\b'*(len(str)+1)
                print str+back,
                VOut = self.outputVSmooth[0] * 14.99/224.7
                AOut = self.outputVSmooth[1] * 1.01/8.3
                socketio.emit('currentValues', {'data': str,'VOut':VOut,'AOut':AOut,'Control':control})
        t = threading.Thread(target=regLoop)
        t.daemon = True
        t.start()

    def setDutyCycle(self,ratio):
        self.pi.set_PWM_dutycycle(outGPIO,int(self.pwmRange*(ratio)))
        
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'targetA':self.targetOutA,'targetV':self.targetOutV},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.targetOutA = D['targetA']
                self.targetOutV = D['targetV']
        except:
            pass
        
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
    charger.targetOutV = param1/100.*256
    return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return charger.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)

@socketio.on('setTargetV')
def setTargetV(arg1):
    charger.targetOutV = int(arg1['data']/100.*256)
    charger.saveParams()

@socketio.on('setTargetA')
def setTargetA(arg1):
    charger.targetOutA = int(arg1['data']/100.*15)
    charger.saveParams()
    
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
    
    