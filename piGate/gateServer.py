from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.baseServer import Server
from BaseClasses.utils import myTimer
from BaseClasses import myLogger
import pdb
import pigpio
import logging
from threading import Timer

app = Flask(__name__)

# Button GPIOS
upButton = 14
downButton = 15

# Motor GPIOS
motorPosGPIO = 16
motorNegGPIO = 17

# Sensor GPIOS
bottomGPIO = 18
topGPIO = 19
pauseGPIO = 20

statusIdle = 0
statusMovingUp = 1
statusMovingDown = 2


class gateServer(Server):
    runStatus = statusIdle
    paused = 0
    
    def onUp(self):
        logging.debug("On Up")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveUp()
        
    def onDown(self):
        logging.debug("On down")
        if self.status == statusMovingUp or self.status == statusMovingDown: self.stop()
        elif self.status == statusIdle: self.moveDown()

    def  __init__(self):
        myLogger.setLogger('gate.log')
        self.scheduler = myTimer()
        
        # Timer to close the window at 23:00 and at 4am
        self.scheduler.addEvent(23,00,self.onDown,[],"Down")
        self.scheduler.addEvent(4,00,self.onDown,[],"Down")
        self.pi = pigpio.pi()
        self.scheduler.start()
        
        def cbf(gpio, level, tick):
            longPress = 0
            logging.debug('cfb0 %d %d %d %d',gpio, level, tick, self.runStatus)
            while self.pi.read(gpio) == 1 and longPress == 0:
                longPress = (self.pi.get_current_tick() - tick)/1.e6 > 1.
                time.sleep(0.010)
            logging.debug('cfb1')
            if gpio == upButton: self.onUp()
            if gpio == downButton: self.onDown()
            if gpio == bottomGPIO and self.status == statusMovingDown: self.stop()
            if gpio == topGPIO and self.status == statusMovingUp: self.stop()
            if gpio == pauseGPIO and self.status == statusMovingDown: self.pause()
        
        def setup(but):
            self.pi.set_mode(but, pigpio.INPUT)
            self.pi.set_pull_up_down(but, pigpio.PUD_DOWN)
            self.pi.set_glitch_filter(but, 10000)
            self.pi.callback(but, 0, cbf)
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
        self.pi.write(motorNegGPIO,0)
        self.pi.write(motorPosGPIO,1)
        self.status = statusMovingUp
        self.paused = 0

    def moveDown(self):
        logging.debug("Move down")
        self.pi.write(motorNegGPIO,1)
        self.pi.write(motorPosGPIO,0)
        self.status = statusMovingDown
        self.paused = 0
        
    def stop(self):
        logging.debug("Stop")
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.status = statusIdle
        self.paused = 0
        
    def pause(self):
        logging.debug("Pause")
        self.pi.write(motorPosGPIO,0)
        self.pi.write(motorNegGPIO,0)
        self.paused = 1
        # Set a timer to come out of pause in a few seconds
        t = Timer(4.0, self.resume,self)
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

