import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from _433 import tx
import time, threading
from BaseClasses import baseServer
import logging
import datetime
from BaseClasses.utils import myTimer
import random

TX_GPIO = 18
BUTTON_GPIO_LV = 17
BUTTON_GPIO_BACK = 21
# Codes for our light remote. > 0 means turn on, < 0 means turn off
codesLivRoom = {1:5510451,-1:5510460,2:5510595,-2:5510604,3:5510915,-3:5510924,4:5512451,-4:5512460,5:5518595,-5:5518604}
codesBedRoom = {6:283955,-6:283964,7:284099,-7:284108,8:284419,-8:284428,9:285955,-9:285964,10:292099,-10:292108}
codesFamRoom = {11:4461875,-11:4461884,12:4462019,-12:4462028,13:4462339,-13:4462348,14:4463875,-14:4463884,15:4470019,-15:4470028}

codes = codesLivRoom
codes.update(codesBedRoom)
codes.update(codesFamRoom)
gateLightNum = 16
codes[gateLightNum]= 4463724
codes[-gateLightNum]=4468884
pathLightNum = 17
codes[pathLightNum]= 4464536
codes[-pathLightNum]=4464572
yardLightNum = 18
codes[yardLightNum]= 4469605
codes[-yardLightNum]=4469635

#codes = codesBedRoom

app = Flask(__name__)    

class lightController(baseServer.Server):

    transmitter = None
    pi = None
    
    lightOffHour = 23
    lightOffMin = 20
    canTurnOff = 1
    pushCount = 10 # so the first callback does nothing. I'm not sure why I'm getting one anyway!
    pushDelayS = .7
    actionTimer = None
    scheduleRandomLight = 0     # Flag to start or not start the random light scheduling
    stopRandomLight = 0         # Flag to stop the current random light loop
    
    lightStatus = {key:0 for key in codes.keys() if key > 0}
    
    def __init__(self):
        logging.info('Starting server')
        super(lightController,self).__init__("rfLights.log")
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.transmitter = tx(self.pi,gpio = TX_GPIO, repeats=10)
        self.pi.set_mode(BUTTON_GPIO_LV, pigpio.INPUT)
        self.pi.set_mode(BUTTON_GPIO_BACK, pigpio.INPUT)
        self.pi.set_pull_up_down(BUTTON_GPIO_LV, pigpio.PUD_UP)
        self.pi.set_glitch_filter(BUTTON_GPIO_LV, 10e3)
        self.pi.set_pull_up_down(BUTTON_GPIO_BACK, pigpio.PUD_UP)
        self.pi.set_glitch_filter(BUTTON_GPIO_BACK, 10e3)
        
        self.myTimer = myTimer()
        def turnOff():
            logging.info('Timer turn lights off')
            self.turnLightOnOff(100,0)
            self.turnLightOnOff(102,0)
        self.myTimer.addEvent(self.lightOffHour,self.lightOffMin,turnOff,[],'Turn lights off')
        def turnLightOnOffRepeat(lightNum,onOff):
            # This is to make 100% sure that we're trying to turn the light on/off
            for ii in range(5):
                self.turnLightOnOff(lightNum,onOff)
                time.sleep(1)
        self.myTimer.addEvent('sunset',5,turnLightOnOffRepeat,[gateLightNum,1],'Turn on gate light')
        self.myTimer.addEvent(1,0,turnLightOnOffRepeat,[gateLightNum,0],'Turn off gate light')
        self.myTimer.addEvent('sunset',10,turnLightOnOffRepeat,[pathLightNum,1],'Turn on path light')
        self.myTimer.addEvent(23,20,turnLightOnOffRepeat,[pathLightNum,0],'Turn off path light')
        self.myTimer.addEvent(23,20,turnLightOnOffRepeat,[yardLightNum,0],'Turn off yard light')
        self.myTimer.addEvent(23,10,self.randomOnOff,[],'Light randomizer start')
        self.myTimer.addEvent(23,30,lambda x: setattr(self,'stopRandomLight',1),[None],'Light randomizer end')
        self.myTimer.start()
        
        turnLightOnOffRepeat(pathLightNum,0)
        turnLightOnOffRepeat(yardLightNum,0)
        
        # Button callback
        def buttonCallback(GPIO, level, tick):
            self.onButton()
        self.pi.callback(BUTTON_GPIO_LV, pigpio.FALLING_EDGE, buttonCallback)
        self.backFlip = 0
        def backButtonCallback(GPIO, level, tick):
            print "BACK BUTTON"
            self.backFlip = 1-self.backFlip
            self.turnLightOnOff(yardLightNum,self.backFlip)
        self.pi.callback(BUTTON_GPIO_BACK, pigpio.FALLING_EDGE, backButtonCallback)

    def randomOnOff(self):
        # pdb.set_trace()
        lightOn = [1,1,1]
        logging.info("randomOnOff called, scheduleRandomLight = %d",self.scheduleRandomLight)
        def randOn():
            delayM = random.randint(2,6)
            #delayM = 1
            # Turn off lights that were previously on
            logging.debug("Random: turning lights off")
            for light in lightOn:
                self.turnLightOnOff(light,0)
                time.sleep(1)
            # Only turn the lights on if we're not stopping.
            if not self.stopRandomLight:
                logging.debug("Random: turning lights on")
                # Turn lights on randomly. I need a way to stop that after 23:00
                # Perhaps it would be nicer to schedule 2 events for each light: an on and an off.
                nextLightOn = random.sample(range(11,16)+range(1,6), len(lightOn))
                for ii,light in enumerate(nextLightOn):
                    self.turnLightOnOff(light,1)
                    lightOn[ii] = light
                    time.sleep(1)
                # If we're not stopping yet, schedule the next random shuffle
                logging.debug("Random: re-scheduling")
                self.myTimer.addDelayedEvent(delayM,randOn,[],'Random event')
            return
        if self.scheduleRandomLight:
            self.stopRandomLight = 0
            logging.info("Random: initial-scheduling")
            self.myTimer.addDelayedEvent(1,randOn,[],'Start random')
        
           
        
    def onButton(self):
        if self.pushCount > 5: self.pushCount = 0
        self.pushCount += 1
        logging.info('Button pressed, pushCount %d',self.pushCount)

        def takeAction():
            logging.info('Take action! %d',self.pushCount)
            pushCount,self.pushCount = self.pushCount,0
            if pushCount == 1: 
                self.turnLightOnOff(100,1)
                self.turnLightOnOff(102,1)
            if pushCount == 2: 
                if self.pi.read(BUTTON_GPIO_LV) == 0:
                    self.turnLightOnOff(102,0)
                    time.sleep(5)
                    self.turnLightOnOff(100,0)
                else:
                    self.turnLightOnOff(100,0)
                    self.turnLightOnOff(102,0)
            if pushCount == 3: self.turnLightOnOff(102,0)
            if pushCount == 4: self.turnLightOnOff(100,0)
            
        try:
            self.actionTimer.cancel()
        except Exception as e:
            logging.warning('Couldnt cancel timer %s',e)
        self.actionTimer = threading.Timer(self.pushDelayS, takeAction, ())
        self.actionTimer.start()
        
    def Index(self):
        return super(lightController,self).Index("index.html")
        # return jsonify(imAlive="I am alive")
        
    def turnLightOnOff(self, lightNum, onOff):
        if lightNum == 100:
            for ii in range(1,6):
                self.turnLightOnOff(ii,onOff)
                self.lightStatus[ii]=onOff
                time.sleep(0.01)
            return
        if lightNum == 101:
            for ii in range(6,11):
                self.turnLightOnOff(ii,onOff)
                self.lightStatus[ii]=onOff
                time.sleep(0.01)
            return
        if lightNum == 102:
            for ii in range(11,16):
                self.turnLightOnOff(ii,onOff)
                self.lightStatus[ii]=onOff
                time.sleep(0.01)
            return
        code = codes[lightNum] if onOff == 1 else codes[-lightNum]
        self.lightStatus[lightNum]=onOff
        self.transmitter.send(code)
        #logging.info('Turning light %d %d',lightNum,onOff)
        
    def getLog(self):
        with open("rfLights.log") as f:
            allLines = f.readlines()
        allLines.reverse()
        return (allLines[0:50])
        
    def getData(self):
        data = {'lightStatus':self.lightStatus[yardLightNum]}
        return data
        
@app.route('/favicon.ico')
def favicon():
    return lc.favicon()
            
@app.route("/reboot")
def reboot():
    return lc.reboot()

@app.route("/getLog")
def getLog():
    return jsonify(lc.getLog())

@app.route("/getData")
def getData():
    return jsonify(lc.getData())

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return lc.Index()

@app.route("/lightOnOff/<int:light_id>/<int:on_off>")
def lightOnOff(light_id,on_off):
    lc.turnLightOnOff(light_id,on_off)
    return ('', 204)
    
lc = lightController()


if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    
    while 1:
        a = raw_input('Command ->[]')
        a = int(a)
        lc.turnLightOnOff(abs(a),a>0)
        
