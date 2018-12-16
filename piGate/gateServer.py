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

# Don't use G14 unless you disable UART!
# 1   2   3   4   5   6   7   8   9   10  11  12  13
#                 
# 5V  5V  Gnd G14 G15 G18 Gnd G23 G24 Gnd G25 G08 G07
# 3V  G02 G03 G04 Gnd G17 G27 G22 3V  G10 G09 G11 Gnd
#              
#

# Left top connector.
# +3.3V
# 2X
# 3X    
# 4     LED
# Gnd
# 17    UP
# 27    DOWN
# 22    TOP
# +3V
# 10    PAUSE
# 9?
# 23 ?
# 15 ?

app = Flask(__name__)

# Button GPIOS
upButton = 17
downButton = 27

# Motor GPIOS
motorPosGPIO = 24
motorNegGPIO = 18

# Sensor GPIOS
bottomGPIO = 10
topGPIO = 22
pauseGPIO = 8

# LED:
ledGPIO = 4

statusIdle = 0
statusMovingUp = 1
statusMovingDown = 2

class gateServer(Server):
    runStatus = statusIdle
    paused = 0
    motorRunTimeUp = 27
    motorRunTimeDown = 35
    status = statusIdle
    
    def onUp(self):
        logging.debug("On Up")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveUp()
        
    def onDown(self):
        logging.debug("On down")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveDown()

    def  __init__(self):
        myLogger.setLogger('gate.log',level=logging.INFO)
        #logging.basicConfig(level=logging.DEBUG)
        self.pi = pigpio.pi()
        self.blinker = utils.blinker(self.pi,ledGPIO)

        # This is for scheduling
        self.scheduler = myTimer()
        # Timer to close the window at 23:00 and at 4am
        self.scheduler.addEvent(4,0,self.onUp,[],'Open window')
        self.scheduler.addEvent(5,0,self.onDown,[],'Close window')
        self.scheduler.start()
        
        # This stops the motor after a few seconds
        self.stopTimer = Timer(0,self.stop)
        
        # Button and GPIO callback function
        def cbf(gpio, level, tick):
            longPress = 0
            print 'Callback {} {} {} run Stat: {}'.format(gpio, level, tick, self.runStatus)
            #logging.debug('Callback %d %d %d run Stat: %d',gpio, level, tick, self.runStatus)
            # while self.pi.read(gpio) == 1 and longPress == 0:
                # longPress = (self.pi.get_current_tick() - tick)/1.e6 > 1.
                # time.sleep(0.010)
            if gpio == upButton: self.onUp()
            if gpio == downButton: self.onDown()
            if gpio == bottomGPIO and self.status == statusMovingDown: self.stop()
            if gpio == topGPIO and self.status == statusMovingUp: self.stop()
            # Only pausing if closing the window.
            if gpio == pauseGPIO and self.status == statusMovingDown: self.pause()
        
        def setup(but):
            self.pi.set_mode(but, pigpio.INPUT)
            self.pi.set_pull_up_down(but, pigpio.PUD_DOWN)
            self.pi.set_glitch_filter(but, 10000)
            self.pi.callback(but, pigpio.RISING_EDGE, cbf)
        # setup all the buttons.
        setup(upButton)
        setup(downButton)
        setup(topGPIO)
        setup(bottomGPIO)
        setup(pauseGPIO)
        self.pi.set_mode(motorPosGPIO, pigpio.OUTPUT)
        self.pi.set_mode(motorNegGPIO, pigpio.OUTPUT)
        self.stop()
        self.blinker.blinkStat = utils.fastBlink
        time.sleep(1)
        self.blinker.blinkStat = utils.flashBlink
            
    def moveUp(self):
        if self.pi.read(topGPIO): return
        self.pi.write(motorNegGPIO,0)
        self.pi.write(motorPosGPIO,1)
        self.blinker.blinkStat = utils.slowBlink
        logging.info("Move up")
        self.stopTimer.cancel()
        self.status = statusMovingUp
        self.paused = 0
        self.stopTimer = Timer(self.motorRunTimeUp, self.stop)
        self.stopTimer.start()

    def moveDown(self):
        if self.pi.read(bottomGPIO): return
        self.pi.write(motorNegGPIO,1)
        self.pi.write(motorPosGPIO,0)
        self.blinker.blinkStat = utils.slowBlink
        logging.info("Move down")
        self.stopTimer.cancel()
        self.status = statusMovingDown
        self.paused = 0
        self.stopTimer = Timer(self.motorRunTimeDown, self.stop)
        self.stopTimer.start()
        
    def stop(self):
        logging.debug("Stop")
        self.stopTimer.cancel()
        self.blinker.blinkStat = utils.flashBlink
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.status = statusIdle
        self.paused = 0
        
    def pause(self):
        self.stopTimer.cancel()
        logging.info("Pause")
        self.blinker.blinkStat = utils.fastBlink
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.paused = 1
        # Set a timer to come out of pause in a few seconds
        t = Timer(4.0, self.resume)
        t.start()
        
    def resume(self):
        logging.info("Resume")
        if self.pi.read(pauseGPIO) == 1: 
            self.pause()
            return
        if self.status == statusMovingUp: self.moveUp()
        if self.status == statusMovingDown: self.moveDown()
        
    def getData(self):
        uptime = self.GetUptime()
        statusStr = "Top switch: {} Bot switch: {} Pause switch: {}".format(self.pi.read(topGPIO),self.pi.read(bottomGPIO),self.pi.read(pauseGPIO))
        return jsonify(uptime=uptime,status=self.status,top=self.pi.read(topGPIO),bottom=self.pi.read(bottomGPIO),pause=
            self.pi.read(pauseGPIO),statusStr=statusStr)
            
    def getLog(self):
        with open('gate.log') as f:
            allLines = f.readlines()
            allLines = list(reversed(allLines))
            return jsonify(log = ''.join(allLines[0:100]))
            
        
        
gs = gateServer()

@app.route('/favicon.ico')
def favicon():
    return gs.favicon()
            
@app.route("/reboot")
def reboot():
    gs.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    gs.kg()
    return ('', 204)

@app.route('/getData')
def getData():
    return gs.getData()

@app.route('/getLog')
def getLog():
    return gs.getLog()

@app.route('/move/<int:updown>')
def move(updown):
    logging.info("HTTP request move: %d",updown)
    if updown > 0: gs.onUp()
    if updown <= 0: gs.onDown()
    return ('', 204)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return gs.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)
    

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=True)
    # while 1:
        # time.sleep(1)

