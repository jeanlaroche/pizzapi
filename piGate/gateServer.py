from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.baseServer import Server
from BaseClasses.utils import myTimer
from BaseClasses import myLogger
import pdb
import pigpio
import logging
import time
from threading import Timer
# 1   2   3   4   5   6   7   8   9   10  11  12  13
#             up  dow 
# 5V  5V  Gnd G14 G15 G18 Gnd G23 G24 Gnd G25 G08 G07
# 3V  G02 G03 G05 Gnd G17 G27 G22 3V  G10 G09 G11 Gnd
#     Mo+ Mo-         bot top pau
#

app = Flask(__name__)

# Button GPIOS
upButton = 14
downButton = 15

# Motor GPIOS
motorPosGPIO = 02
motorNegGPIO = 03

# Sensor GPIOS
bottomGPIO = 17
topGPIO = 27
pauseGPIO = 22

statusIdle = 0
statusMovingUp = 1
statusMovingDown = 2


class gateServer(Server):
    runStatus = statusIdle
    paused = 0
    motorRunTime = 20
    
    def onUp(self):
        logging.debug("On Up")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveUp()
        
    def onDown(self):
        logging.debug("On down")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveDown()

    def  __init__(self):
        myLogger.setLogger('gate.log',level=logging.DEBUG)
        # This is for scheduling
        self.scheduler = myTimer()
        # This stops the motor after a few seconds
        self.stopTimer = Timer(0,self.stop)
        
        # Timer to close the window at 23:00 and at 4am
        self.scheduler.addEvent(20,13,self.onDown,[],"Down")
        self.scheduler.addEvent(20,14,self.onUp,[],"Up")
        self.pi = pigpio.pi()
        self.scheduler.start()
        
        # Button and GPIO callback function
        def cbf(gpio, level, tick):
            longPress = 0
            logging.debug('Callback %d %d %d run Stat: %d',gpio, level, tick, self.runStatus)
            while self.pi.read(gpio) == 1 and longPress == 0:
                longPress = (self.pi.get_current_tick() - tick)/1.e6 > 1.
                time.sleep(0.010)
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
            self.pi.callback(but, 0, cbf)
        # setup all the buttons.
        setup(upButton)
        setup(downButton)
        setup(topGPIO)
        setup(bottomGPIO)
        setup(pauseGPIO)
        self.pi.set_mode(motorPosGPIO, pigpio.OUTPUT)
        self.pi.set_mode(motorNegGPIO, pigpio.OUTPUT)
        self.stop()
            
    def moveUp(self):
        logging.debug("Move up")
        self.stopTimer.cancel()
        self.pi.write(motorNegGPIO,0)
        self.pi.write(motorPosGPIO,1)
        self.status = statusMovingUp
        self.paused = 0
        self.stopTimer = Timer(self.motorRunTime, self.stop)
        self.stopTimer.start()

    def moveDown(self):
        logging.debug("Move down")
        self.stopTimer.cancel()
        self.pi.write(motorNegGPIO,1)
        self.pi.write(motorPosGPIO,0)
        self.status = statusMovingDown
        self.paused = 0
        self.stopTimer = Timer(self.motorRunTime, self.stop)
        self.stopTimer.start()
        
    def stop(self):
        logging.debug("Stop")
        self.stopTimer.cancel()
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.status = statusIdle
        self.paused = 0
        
    def pause(self):
        self.stopTimer.cancel()
        logging.debug("Pause")
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.paused = 1
        # Set a timer to come out of pause in a few seconds
        t = Timer(4.0, self.resume)
        t.start()
        
    def resume(self):
        logging.debug("Resume")
        if self.pi.read(pauseGPIO) == 1: 
            self.pause()
            return
        if self.status == statusMovingUp: self.moveUp()
        if self.status == statusMovingDown: self.moveDown()
        
        
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

@app.route('/move/<int:updown>')
def move(updown):
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
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=True)

