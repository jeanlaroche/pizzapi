from flask import Flask, render_template, request, jsonify
import readTemp as rt
import pdb
import threading, time
import schedule
import re

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	return render_template("index.html", uptime=GetUptime())

@app.route("/_tempUp")
def _tempUp():
	# rt.pressTempAdjust()
	rt.incSetTemperature(1)
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_tempDown")
def _tempDown():
	rt.incSetTemperature(-1)
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_getTubStatus")
def _getTubStatus():
	# Don't read the temperature if the tub is in the process of adjusting it.
	if not rt.isAdjustingTemp: rt.readTemperature(updateTempVal=1)
	heatValStr = "ON" if rt.heaterVal else "OFF"
	heaterStats = "Heater ON for {:.2f}h out of {:.2f} or {:.2f}h per day".format(rt.totTimeHeaterOn,rt.totTimeHeater,24*rt.totTimeHeaterOn/rt.totTimeHeater if rt.totTimeHeater else 0.0)
 	return jsonify(temperatureValue=rt.temperatureVal,heaterValue = heatValStr,targetTemperatureValue=rt.targetTemperatureVal,setTemperatureValue=rt.setTemperatureVal,upTime = GetUptime(),lastMessage=rt.lastMessage,heaterStats = heaterStats)

@app.route("/_getFullData")
def _getFullData():
	print "INIT CALLED"
	rt.setup()
	rt.init()
	return ""

@app.route("/_pageUnload")
def _pageUnload():
	print "PAGE UNLOADED"
	return ""
	
@app.route("/_schedule")
def _schedule():
	print "RERUN SCHEDULE"
	schedule.redoSchedule()
	return ""
	

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	if rt.fakeIt: uptime = "14:29:08 up 33 days, 10:36,  1 user,  load average: 0.16, 0.03, 0.01"
	else: uptime = check_output(["uptime"])
	uptime=re.sub('[\d]+ user[s]*,.*load(.*),.*,.*','load\\1',uptime)
	return uptime
	
def showHeartBeat():
	rt.showHeartBeat()
	rt.logHeaterUse()
	if rt.fakeIt: return
	tim = threading.Timer(2, showHeartBeat)
	tim.start()
	
# run the webserver on standard port 80, requires sudo
if __name__ == "__main__":
	# Pins.Init()
	rt.setup()
	rt.init()
	showHeartBeat()
	# Start scheduler
	tim = threading.Timer(1, schedule.openAndRun)
	tim.start()
	app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
	rt.tearDown()
