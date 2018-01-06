from flask import Flask, render_template, request, jsonify, send_from_directory
import pdb
import threading, time, os
import re
import mushroom
import numpy as np

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

statsDay = 0  # 0 for today, -1 for yesterday, -2 etc
allowControl = 0  # Allow or disallow control of humidity
alwaysAllow = 0  # Ignore flag above.
mush = None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    global alwaysAllow
    alwaysAllow = 0
    return render_template("index.html", uptime=GetUptime())


# special private page that allows changing the humidity. For lack of a proper login thingy
@app.route("/Pook")
def Index2():
    global alwaysAllow
    alwaysAllow = 1
    return render_template("index.html", uptime=GetUptime())

@app.route("/_humidityUp")
def _humidityUp():
    print "HUMIDITY UP"
    mush.incTargetHumidity(1)
    return jsonify(targetHumidity=int(mush.targetHumidity))
        # if allowControl or alwaysAllow: rt.incSetHumidityerature(1)
        # return jsonify(targetHumidityeratureValue=rt.targetHumidityeratureVal)

@app.route("/_humidityDown")
def _humidityDown():
    print "Humidity Down"
    mush.incTargetHumidity(-1)
    return jsonify(targetHumidity=int(mush.targetHumidity))
    # if allowControl or alwaysAllow: rt.incSetHumidityerature(-1)
        # return jsonify(targetHumidityeratureValue=rt.targetHumidityeratureVal)

@app.route("/_fanTest")
def _fanTest():
    print "FAN Test"
    mush.fanTest()

@app.route("/_fanUp")
def _fanUp():
    print "FAN Plus"
    mush.incFanFreqDur(incFreqMin= .5 if mush.fanOnPeriodMin < 5 else 1)
    return jsonify(fanOnPeriodMin = mush.fanOnPeriodMin)

@app.route("/_fanDown")
def _fanDown():
    print "FAN Down"
    mush.incFanFreqDur(incFreqMin= -.5 if mush.fanOnPeriodMin < 5 else -1)
    return jsonify(fanOnPeriodMin = mush.fanOnPeriodMin)

@app.route("/_fanDurUp")
def _fanDurUp():
    print "FAN DurPlus"
    mush.incFanFreqDur(incDurS=10)
    return jsonify(fanOnLengthS = mush.fanOnLengthS)

@app.route("/_fanDurDown")
def _fanDurDown():
    print "FAN DurDown"
    mush.incFanFreqDur(incDurS=-10)
    return jsonify(fanOnLengthS = mush.fanOnLengthS)

    
@app.route("/_pageUnload")
def _pageUnload():
    print "PAGE UNLOADED"
    return ""

@app.route("/_getData")
def _getData():
    print "Get Data"
    curHumidity = np.round(mush.curHumidity,decimals=1)
    X,Y = mush.getHumidityData(12)
    # stats= mush.grabLog()
    # stats = ''.join(stats)
    # stats,X,Y = schedule.computeGraphData()
    # print stats
    return jsonify(curHumidity=curHumidity,targetHumidity=int(mush.targetHumidity),humidity=mush.curHumidity,upTime=GetUptime(),fanStatus=mush.fanStatus,humStatus=mush.humStatus,curTemp=mush.curTemp,fanOnPeriodMin=mush.fanOnPeriodMin,fanOnLengthS=mush.fanOnLengthS,X=X,Y=Y)


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
    global mush
    print "RUNNING PRESTART"
    mush = mushroom.mushroomControl()
    #mush.draw()

# rt.setup()
# rt.init()
# Start the heartbeat after a few seconds.

preStart()

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
    #_getData()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    mush.close()
    print "TEARDOWN"
