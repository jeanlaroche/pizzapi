from flask import Flask, render_template, request, jsonify, send_from_directory
import readTemp as rt
import pdb
import threading, time, os
import schedule as sc
import re
import Adafruit_DHT
sensor = Adafruit_DHT.DHT11

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

statsDay			= 	0	# 0 for today, -1 for yesterday, -2 etc
allowControl 		= 	0	# Allow or disallow control of temp
alwaysAllow 		= 	0	# Ignore flag above.

humidity = 0
airTemp = 0
minAirTemp = 200
maxAirTemp = -100

def getTemp():
	global humidity, airTemp, maxAirTemp, minAirTemp
	hum, air = Adafruit_DHT.read_retry(sensor, 2)
	if hum is not None and air is not None and air is not 0:
		humidity = hum
		if airTemp == 0: airTemp = 32+1.8*air
		else: airTemp = .95*airTemp + 0.05*(32+1.8*air)
		airTemp = round(airTemp,1)
		maxAirTemp = max(airTemp,maxAirTemp)
		minAirTemp = min(airTemp,minAirTemp)
	return humidity,airTemp

@app.route('/airTemp')
def _airTemp():
	getTemp()
	return jsonify(humidity=humidity,outsideTemperature=airTemp,minAirTemp=minAirTemp,maxAirTemp=maxAirTemp)

@app.route('/favicon.ico')
def favicon():
	return send_from_directory(app.root_path,'favicon.ico', mimetype='image/vnd.microsoft.icon')
	
# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	global alwaysAllow
	alwaysAllow = 0
	return render_template("index.html", uptime=GetUptime())

# special private page that allows changing the temp. For lack of a proper login thingy
@app.route("/Pook")
def Index2():
	global alwaysAllow
	alwaysAllow = 1
	return render_template("index.html", uptime=GetUptime())
	
@app.route("/_tempUp")
def _tempUp():
	if allowControl or alwaysAllow: rt.incSetTemperature(1)
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_tempDown")
def _tempDown():
	if allowControl or alwaysAllow: rt.incSetTemperature(-1)
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_getTubStatus")
def _getTubStatus():
	global allowControl
	allowControl = True if ('192.168' in request.referrer) else False
	#print "IP: {} Allow: {}".format(request.referrer,allowControl)
	heatValStr = "ON" if rt.heaterVal else "OFF"
	heaterTime,heaterValue,heaterUsage,heaterTotalUsage,thisDayStr,prevDayStr,nextDayStr,stats = sc.computeGraphData()
	heaterTicks = range(0,25)
	heaterLabel = ["{:}".format(ii) for ii in range(0,25)]
	fileUpdated = sc.fileUpdated
	sc.fileUpdated = 0
	getTemp()
 	return jsonify(temperatureValue=rt.temperatureVal,heaterValueStr = heatValStr,targetTemperatureValue=rt.targetTemperatureVal,setTemperatureValue=rt.setTemperatureVal,upTime = GetUptime(),lastMessage=rt.lastMessage,heaterStats = [heaterUsage,heaterTotalUsage], heaterTime = heaterTime, heaterValue = heaterValue,heaterLabel = heaterLabel,heaterTicks=heaterTicks,thisDayStr=thisDayStr,prevDayStr=prevDayStr,nextDayStr=nextDayStr,newHeaterData = fileUpdated, stats=stats, allowControl=allowControl or alwaysAllow,outsideTemperature=airTemp,minAirTemp=minAirTemp,maxAirTemp=maxAirTemp)

@app.route("/_getFullData")
def _getFullData():
	print "GET_FULL_DATA"
	rt.setup()
	# Call this in a separate thread so we can return immediately.
	tim = threading.Timer(0.1, rt.init)
	tim.start()
	# rt.init()
	return ""

@app.route("/_onNextDay")
def _onNextDay():
	if sc.statsDay < 0 : sc.statsDay += 1
	# pdb.set_trace()
	return ""

@app.route("/_onPrevDay")
def _onPrevDay():
	sc.statsDay -= 1
	return ""

@app.route("/_onToday")
def _onToday():
	sc.statsDay = 0
	return ""

@app.route("/_onMinusWeek")
def _onMinusWeek():
	sc.statsDay -= 7
	return ""

@app.route("/_onPlusWeek")
def _onPlusWeek():
	if sc.statsDay < -6 : sc.statsDay += 7
	return ""
	
@app.route("/_pageUnload")
def _pageUnload():
	print "PAGE UNLOADED"
	return ""
	
@app.route("/_schedule")
def _schedule():
	print "RERUN SCHEDULE"
	if allowControl or alwaysAllow: sc.redoSchedule()
	return ""
	

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	if rt.fakeIt: uptime = "14:29:08 up 33 days, 10:36,  1 user,  load average: 0.16, 0.03, 0.01"
	else: uptime = check_output(["uptime"])
	uptime=re.sub('[\d]+ user[s]*,.*load(.*),.*,.*','load\\1',uptime)
	return uptime
	
def showHeartBeat():
	global minAirTemp, maxAirTemp
	if rt.fakeIt: return
	# Don't read the temperature if the tub is in the process of adjusting it.
	if not rt.isAdjustingTemp:  rt.readTemperature(updateTempVal=1)
	sc.logHeaterUse()
	os.system('touch ' + rt.logFile)
	locTime = time.localtime()
	if locTime.tm_hour == 2 and locTime.tm_min == 0: 
		minAirTemp,maxAirTemp = airTemp,airTemp
	
	#rt.mprint("HeartBeat")
	tim = threading.Timer(4, showHeartBeat)
	tim.start()
	
# run the webserver on standard port 80, requires sudo
#if __name__ == "__main__":
# Pins.Init()
def preStart():
	print "RUNNING PRESTART"
	rt.setup()
	rt.init()
	# Start the heartbeat after a few seconds.
	tim = threading.Timer(4, showHeartBeat)
	tim.start()
	# Start scheduler after a while
	tim = threading.Timer(8, sc.openAndRun)
	tim.start()

preStart()

# NOTE: When using gunicorn, apparently server.py is loaded, and then the app is run. If you want to initialize stuff, you have
# to do it as above, by a call to "prestart"
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8080, debug=True, threaded = False, use_reloader=True)
	print "TEARDOWN"
	rt.tearDown()
	