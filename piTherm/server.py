from flask import Flask, render_template, request, jsonify, send_from_directory
import pdb
import threading, time, os
import re
import heaterControl
import numpy as np
import schedule

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

statsDay = 0  # 0 for today, -1 for yesterday, -2 etc
allowControl = 0  # Allow or disallow control of temp
alwaysAllow = 0  # Ignore flag above.
hc = None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    global alwaysAllow
    alwaysAllow = 0
    return render_template("index.html", uptime=GetUptime())


# special private page that allows changing the temp. For lack of a proper login thingy
@app.route("/reboot")
def reboot():
    os.system('sudo reboot now')

@app.route("/Pook")
def Index2():
    global alwaysAllow
    alwaysAllow = 1
    return render_template("index.html", uptime=GetUptime())

@app.route("/_tempUp")
def _tempUp():
    #print "TEMP UP"
    hc.incTargetTemp(1)
    return jsonify(targetTemp=int(hc.targetTemp))
        # if allowControl or alwaysAllow: rt.incSetTemperature(1)
        # return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_tempDown")
def _tempDown():
    #print "Temp Down"
    hc.incTargetTemp(-1)
    return jsonify(targetTemp=int(hc.targetTemp))
    # if allowControl or alwaysAllow: rt.incSetTemperature(-1)
        # return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_schedule")
def _schedule():
    #print "Schedule"
    hc.onRun()
    return ""

@app.route("/_hold")
def _hold():
    #print "HOLD"
    hc.onHold()
    return jsonify(holding=hc.holding)
    
@app.route("/_pageUnload")
def _pageUnload():
    #print "PAGE UNLOADED"
    return ""

@app.route("/_getData")
def _getData():
    #print "Get Data"
    roomTemp = np.round(hc.roomTemp,decimals=1)
    # stats= hc.grabLog()
    # stats = ''.join(stats)
    stats,X,Y = schedule.computeGraphData()
    return jsonify(roomTemp=roomTemp,targetTemp=int(hc.targetTemp),humidity=hc.humidity,upTime=GetUptime(),heaterOn=hc.heaterOn,lastMsg=hc.lastMsg,stats=stats,holding=hc.holding,X=X,Y=Y,outsideTemp=hc.outsideTemp,outsideHum=round(hc.outsideHum,0))


def GetUptime():
    # get uptime from the linux terminal command
    from subprocess import check_output
    uptime = check_output(["uptime"])
    uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime)
    return uptime


# run the webserver on standard port 80, requires sudo
# if __name__ == "__main__":
# Pins.Init()
def preStart():
    global hc
    #print "RUNNING PRESTART"
    hc = heaterControl.heaterControl(doStart=1)
    #hc.draw()

# rt.setup()
# rt.init()
# Start the heartbeat after a few seconds.

preStart()

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    _getData()
    app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    hc.close()
    #print "TEARDOWN"
