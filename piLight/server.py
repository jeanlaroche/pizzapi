from flask import Flask, render_template, request, jsonify, send_from_directory
from threading import Timer
import pdb
import re
import threading, time, os
import RPi.GPIO as GPIO
from BaseClasses import myLogger

# Can use this for the sunset time: https://en.wikipedia.org/wiki/Sunrise_equation

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html

app = Flask(__name__)
log = None

class Server(object):
    pathLightGPIO = 4 # Pins 4 from SDcard on the inside. 5 is GND
    lightGPIO = 17 # Pins 4 from SDcard on the inside. 5 is GND
    statsDay = 0  # 0 for today, -1 for yesterday, -2 etc
    allowControl = 0  # Allow or disallow control of temp
    alwaysAllow = 0  # Ignore flag above.
    pathLightStatus = 0
    lightStatus = 0
    canTurnOn = 1
    canTurnOff = 1
    onHour = 0
    onMin  = 0
    onTimeOffsetMin = 15
    
    offHour = 23
    offMin  = 15

    def  __init__(self):
        global log
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pathLightGPIO, GPIO.OUT)
        GPIO.setup(self.lightGPIO, GPIO.OUT)
        # This is so self.offTimer exists!
        self.offTimer = Timer(600, lambda x: x, (0))
        self.setPathLightOnOff(0)
        self.setLightOnOff(0)
        LL = myLogger.myLogger('./lights.log')
        log=LL.getLogger()
        
        def timerLoop():
            return self.timerLoop()
        T = threading.Thread(target=timerLoop, args = ())
        T.daemon = True
        T.start()
        pass
    
    def favicon(self):
        return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
        
    # return index page when IP address of RPi is typed in the browser
    def Index(self):
        return render_template("index.html", uptime=self.GetUptime())
    
    def reboot(self):
        os.system('sudo reboot now')
        
    def setPathLightOnOff(self,isOn):
        self.pathLightStatus = isOn
        GPIO.output(self.pathLightGPIO,1-self.pathLightStatus)
    def setLightOnOff(self,isOn):
        self.lightStatus = isOn
        GPIO.output(self.lightGPIO,1-self.lightStatus)

    def _PathOn(self):
        log.info("PATH ON")
        self.setPathLightOnOff(1)
        self.turnOffInMin(60)
        return jsonify(pathLightStatus=int(self.pathLightStatus))

    def _PathOff(self):
        log.info("PATH OFF")
        self.setPathLightOnOff(0)
        return jsonify(pathLightStatus=int(self.pathLightStatus))

    def _LightOn(self):
        log.info("LIGHT ON")
        self.setLightOnOff(1)
        self.turnOffInMin(60)
        return jsonify(lightStatus=int(self.lightStatus))

    def _LightOff(self):
        log.info("LIGHT OFF")
        self.setLightOnOff(0)
        return jsonify(lightStatus=int(self.lightStatus))

    def _getData(self):
        #log.info("GET DATA")
        sunrise,sunset = self.getSunsetTime()[2:]
        def cleanup(str):
            #log.info(str)
            str = re.sub('\d+\-\d+\-\d+ ','',str)
            str = re.sub(':\d\d\..*','',str)
            #log.info(str)
            return str
        return jsonify(sunrise=cleanup(sunrise),sunset=cleanup(sunset),uptime=self.GetUptime(),pathLightStatus=self.pathLightStatus,lightStatus=self.lightStatus)

    def turnOffInMin(self,delayMin):
        def offWithYourHead():
            log.info("Turning off from timer")
            self.setPathLightOnOff(0)
            self.setLightOnOff(0)
        if self.canTurnOn:
            # This means we're outside of the time period where the schedule will turn the lights off. 
            log.info("Starting off timer %d mn",delayMin)
            self.offTimer.cancel()
            self.offTimer = Timer(delayMin*60, offWithYourHead, ())
            self.offTimer.start()
        
    def GetUptime(self):
        # get uptime from the linux terminal command
        from subprocess import check_output
        uptime = check_output(["uptime"])
        uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime)
        return uptime+" Path is {} Lights are {}".format('on' if self.pathLightStatus else 'off','on' if self.lightStatus else 'off')

    def getSunsetTime(self):
        import ephem  
        o=ephem.Observer()  
        o.lat='36.97'  
        o.long='-122.03'  
        s=ephem.Sun()  
        s.compute()
        sunrise = "Next sunrise: {}".format(ephem.localtime(o.next_rising(s)))
        sunset = "Next sunset: {}".format(ephem.localtime(o.next_setting(s)))
        LT = ephem.localtime(o.next_setting(s))
        import datetime
        LT = LT+datetime.timedelta(minutes=self.onTimeOffsetMin)
        return LT.hour,LT.minute,sunrise,sunset
        

    def timerLoop(self):
        while 1:
            try:
                # Get the time of day. Find out if the light should be on. 
                locTime = time.localtime()
                if locTime.tm_hour == self.onHour and locTime.tm_min == self.onMin and self.canTurnOn == 1:
                    log.info("TIMER ON")
                    self.setPathLightOnOff(1)
                    self.canTurnOn = 0
                    self.canTurnOff = 1
                    self.offTimer.cancel()
                if locTime.tm_hour == self.offHour and locTime.tm_min == self.offMin and self.canTurnOff == 1:
                    log.info("TIMER OFF")
                    self.setPathLightOnOff(0)
                    self.setLightOnOff(0)
                    self.canTurnOn = 1
                    self.canTurnOff = 0
                    self.offTimer.cancel()
                pass
            except:
                log.errir("Exception")
            self.onHour,self.onMin=self.getSunsetTime()[0:2]
            log.info("Timer, time: %d:%d -- onTime %d:%d -- offTime %d:%d",locTime.tm_hour,locTime.tm_min,self.onHour,self.onMin,self.offHour,self.offMin)
            time.sleep(15)

@app.route('/favicon.ico')
def favicon():
    return server.favicon()
            
@app.route("/reboot")
def reboot():
    return server.reboot()

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return server.Index()

@app.route("/_PathOn")
def _PathOn():
    return server._PathOn()

@app.route("/_PathOff")
def _PathOff():
    return server._PathOff()

@app.route("/_LightOn")
def _LightOn():
    return server._LightOn()

@app.route("/_LightOff")
def _LightOff():
    return server._LightOff()

@app.route("/_getData")
def _getData():
    return server._getData()

server = Server()

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
