from flask import Flask, render_template, request, jsonify, send_from_directory
import pdb
import re
import threading, time, os
import RPi.GPIO as GPIO

pathLightGPIO = 17 # Pins 4 from SDcard on the inside. 5 is GND
lightGPIO = 18 # Pins 4 from SDcard on the inside. 5 is GND
GPIO.setmode(GPIO.BCM)
GPIO.setup(pathLightGPIO, GPIO.OUT)
GPIO.setup(lightGPIO, GPIO.OUT)

# Can use this for the sunset time: https://en.wikipedia.org/wiki/Sunrise_equation

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html

app = Flask(__name__)

statsDay = 0  # 0 for today, -1 for yesterday, -2 etc
allowControl = 0  # Allow or disallow control of temp
alwaysAllow = 0  # Ignore flag above.

pathLightStatus = 0
lightStatus = 0
GPIO.output(pathLightGPIO,pathLightStatus)
GPIO.output(lightGPIO,lightStatus)
canTurnOn = 1
canTurnOff = 1

onHour = 0
onMin  = 0
offHour = 23
offMin  = 15

fd = open('./lights.log','w',0)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/reboot")
def reboot():
    os.system('sudo reboot now')

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    global alwaysAllow
    alwaysAllow = 0
    return render_template("index.html", uptime=GetUptime())

@app.route("/_PathOn")
def _PathOn():
    global pathLightStatus
    mprint("PATH ON")
    pathLightStatus = 1
    GPIO.output(pathLightGPIO,pathLightStatus)
    return jsonify(pathLightStatus=int(pathLightStatus))

@app.route("/_PathOff")
def _PathOff():
    global pathLightStatus
    mprint("PATH OFF")
    pathLightStatus = 0
    GPIO.output(pathLightGPIO,pathLightStatus)
    return jsonify(pathLightStatus=int(pathLightStatus))

@app.route("/_LightOn")
def _LightOn():
    global lightStatus
    mprint("LIGHT ON")
    lightStatus = 1
    GPIO.output(lightGPIO,lightStatus)
    return jsonify(lightStatus=int(lightStatus))

@app.route("/_LightOff")
def _LightOff():
    global lightStatus
    mprint("LIGHT OFF")
    lightStatus = 0
    GPIO.output(lightGPIO,lightStatus)
    return jsonify(lightStatus=int(lightStatus))

@app.route("/_getData")
def _getData():
    #mprint("GET DATA")
    sunrise,sunset = getSunsetTime()[2:]
    def cleanup(str):
        #mprint(str)
        str = re.sub('\d+\-\d+\-\d+ ','',str)
        str = re.sub(':\d\d\..*','',str)
        #mprint(str)
        return str
    return jsonify(sunrise=cleanup(sunrise),sunset=cleanup(sunset),uptime=GetUptime(),pathLightStatus=pathLightStatus,lightStatus=lightStatus)

def mprint(aString):
    print(aString)
    fd.write(aString+'\n')
    
def GetUptime():
    # get uptime from the linux terminal command
    from subprocess import check_output
    uptime = check_output(["uptime"])
    uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime)
    return uptime+" Path is {} Lights are {}".format('on' if pathLightStatus else 'off','on' if lightStatus else 'off')

def getSunsetTime():
    import ephem  
    o=ephem.Observer()  
    o.lat='36.97'  
    o.long='-122.03'  
    s=ephem.Sun()  
    s.compute()
    sunrise = "Next sunrise: {}".format(ephem.localtime(o.next_rising(s)))
    sunset = "Next sunset: {}".format(ephem.localtime(o.next_setting(s)))
    LT = ephem.localtime(o.next_setting(s))
    return LT.hour,LT.minute,sunrise,sunset
    

def timerLoop():
    global pathLightStatus, lightStatus, canTurnOn, canTurnOff, onHour,onMin,offHour,offMin
    while 1:
        try:
            # Get the time of day. Find out if the light should be on. 
            locTime = time.localtime()
            if locTime.tm_hour == onHour and locTime.tm_min == onMin and canTurnOn == 1:
                mprint("TIMER ON")
                pathLightStatus = 1
                GPIO.output(pathLightGPIO,pathLightStatus)
                canTurnOn = 0
                canTurnOff = 1
            if locTime.tm_hour == offHour and locTime.tm_min == offMin and canTurnOff == 1:
                mprint("TIMER OFF")
                pathLightStatus = 0
                lightStatus = 0
                GPIO.output(pathLightGPIO,pathLightStatus)
                GPIO.output(lightGPIO,lightStatus)
                canTurnOn = 1
                canTurnOff = 0
            pass
        except:
            mprint("Exception")
        onHour,onMin=getSunsetTime()[0:2]
        mprint("Timer, time: {}:{} -- onTime {}:{} -- offTime {}:{}".format(locTime.tm_hour,locTime.tm_min,onHour,onMin,offHour,offMin))
        time.sleep(15)

# run the webserver on standard port 80, requires sudo
# if __name__ == "__main__":
# Pins.Init()
def preStart():
    # Start the timer loop
    T = threading.Thread(target=timerLoop, args = ())
    T.daemon = True
    T.start()
    pass

preStart()
# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
