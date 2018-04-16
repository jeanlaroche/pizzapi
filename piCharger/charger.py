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
    posToAdcV = 256./100
    posToAdcA = 150./100
    dacToVolt = 14.84/224.7
    dacToAmp = 0.168/8.3
    paramFile = 'params.json'
    mAmpHour = 0
    lastAmpHourTime = 0
    
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
        self.PowerOn = 0
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
                    ratioA = controlFun(ratioA,delta,mult=4,deadZone=0)
                    # But pick the minimum of the two.
                    ratio,control = min(ratioV,ratioA),'V' if ratioV < ratioA else 'A'
                    ratioA,ratioV=ratio,ratio
                    self.setDutyCycle(ratio)
                else:
                    self.setDutyCycle(0)
                time.sleep(0.0001)
                str = "{:.1f}V {:.1f}A tarV {:.0f} tarA {:.0f} ratio {:.0f}({}) -- {}   ".format(self.outputV[0],self.outputV[1], self.targetOutV, self.targetOutA, ratio*self.pwmRange, control, self.counter)
                str = "V{:.1f} A{:.1f} tarV {:.0f} tarA {:.0f} ratio {:.0f}   ".format(self.outputV[0],self.outputV[1], self.targetOutV, self.targetOutA, ratio*self.pwmRange)
                back = '\b'*(len(str)+1)
                print str+back,
                VMax = self.targetOutV * self.dacToVolt
                AMax = self.targetOutA * self.dacToAmp
                VOut = self.outputVSmooth[0] * self.dacToVolt
                AOut = self.outputVSmooth[1] * self.dacToAmp
                Power = VOut*AOut
                thisTime = time.time()
                if self.PowerOn:
                    if self.lastAmpHourTime == 0: self.lastAmpHourTime = thisTime
                    if thisTime > self.lastAmpHourTime+2:
                        self.mAmpHour += (thisTime-self.lastAmpHourTime)*Power/3.6
                        self.lastAmpHourTime = thisTime
                        logging.info("mAmpHour: {:.2f}mWh".format(self.mAmpHour))
                    
                socketio.emit('currentValues', {'data': str,'VOut':VOut,'AOut':AOut,'VMax':VMax,'AMax':AMax,'Control':control,
                    'PowerOn':self.PowerOn,'Power':Power,'mAmpHour':self.mAmpHour})
        t = threading.Thread(target=regLoop)
        t.daemon = True
        t.start()

    def turnOn(self,onOrOff):
        if self.PowerOn == 0 and onOrOff == 1:
            self.lastAmpHourTime = 0
            self.mAmpHour = 0
        self.PowerOn = onOrOff
        
    def calibrate(self,AorV):
        if AorV == "V":
            # The actual voltage is supposed to be 6V.
            self.dacToVolt = 6. / self.outputVSmooth[0]
        else:
            self.dacToAmp = 1. / self.outputVSmooth[1]
        self.saveParams()

    def setDutyCycle(self,ratio):
        self.pi.set_PWM_dutycycle(outGPIO,int(self.pwmRange*(ratio)))
        
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'targetA':self.targetOutA,'targetV':self.targetOutV,'dacToVolt':self.dacToVolt,'dacToAmp':self.dacToAmp},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.targetOutA = D['targetA']
                self.targetOutV = D['targetV']
                self.dacToVolt = D['dacToVolt']
                self.dacToAmp = D['dacToAmp']
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

@app.route('/_init')
def init():
    return(jsonify(VOut=charger.targetOutV/charger.posToAdcV,AOut=charger.targetOutA/charger.posToAdcA))

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
    charger.targetOutV = int(arg1['data']*charger.posToAdcV)
    charger.saveParams()

@socketio.on('setTargetA')
def setTargetA(arg1):
    charger.targetOutA = int(arg1['data']*charger.posToAdcA)
    charger.saveParams()

@socketio.on('TurnOnOff')
def turnOnOff(arg1):
    print "TURNING ON?OFF {}".format(arg1['data'])
    charger.turnOn(int(arg1['data']))

@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    charger.calibrate(arg1['data'])

    
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
    
    