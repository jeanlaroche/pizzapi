from flask import Flask, render_template, request, jsonify
import readTemp as rt
import pdb
import threading, time, os
import schedule as sc
import re

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

statsDay			= 	0	# 0 for today, -1 for yesterday, -2 etc

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
	heatValStr = "ON" if rt.heaterVal else "OFF"
	statString = sc.computeStats()[0]
	# Get the stats from sc.
	today = sc.getToday()
	curTime = sc.getCtime()
	tempTime = [item[0] for item in sc.tempData]
	tempValue = [item[1] for item in sc.tempData]
	# For the heater we want to display steps when the heater goes from 0 to 1 or 1 to 0
	# For this, we need to duplicate each entry.
	A = [item for item  in sc.heaterData if item[0] < today+statsDay*24+24 and item[0] > today+statsDay*24]
	B = [];
	for item in A:
		B.append(item[:])		# Careful! If you use item you'll get a reference, not a copy.
		B[-1][1] = 1-B[-1][1]	# Flip value.
		B.append(item[:])
	heaterTime = [item[0]-today-statsDay*24 for item in B]
	heaterValue = [item[1] for item in B]
	heaterLabel = []
	heaterTicks = []
	# Putting tick marks every hour, with a label for the hour of the day.
	for ii in range(0,25):
		heaterLabel.append("{:}".format(ii))
		heaterTicks.append(ii)
 	return jsonify(temperatureValue=rt.temperatureVal,heaterValueStr = heatValStr,targetTemperatureValue=rt.targetTemperatureVal,setTemperatureValue=rt.setTemperatureVal,upTime = GetUptime(),lastMessage=rt.lastMessage,heaterStats = statString, tempTime = tempTime, tempValue = tempValue,heaterTime = heaterTime, heaterValue = heaterValue,heaterLabel = heaterLabel,heaterTicks=heaterTicks)

@app.route("/_getFullData")
def _getFullData():
	print "INIT CALLED"
	rt.setup()
	rt.init()
	return ""

@app.route("/_onNextDay")
def _onNextDay():
	global statsDay
	if statsDay < 0 : statsDay += 1
	return ""

@app.route("/_onPrevDay")
def _onPrevDay():
	global statsDay
	statsDay -= 1
	return ""

@app.route("/_pageUnload")
def _pageUnload():
	print "PAGE UNLOADED"
	return ""
	
@app.route("/_schedule")
def _schedule():
	print "RERUN SCHEDULE"
	sc.redoSchedule()
	return ""
	

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	if rt.fakeIt: uptime = "14:29:08 up 33 days, 10:36,  1 user,  load average: 0.16, 0.03, 0.01"
	else: uptime = check_output(["uptime"])
	uptime=re.sub('[\d]+ user[s]*,.*load(.*),.*,.*','load\\1',uptime)
	return uptime
	
def showHeartBeat():
	if rt.fakeIt: return
	# Don't read the temperature if the tub is in the process of adjusting it.
	if not rt.isAdjustingTemp:  rt.readTemperature(updateTempVal=1)
	sc.logHeaterUse()
	os.system('touch ' + rt.logFile)
	tim = threading.Timer(4, showHeartBeat)
	tim.start()
	
# run the webserver on standard port 80, requires sudo
if __name__ == "__main__":
	# Pins.Init()
	rt.setup()
	rt.init()
	# Start the heartbeat after a few seconds.
	tim = threading.Timer(4, showHeartBeat)
	tim.start()
	# Start scheduler after a while
	tim = threading.Timer(8, sc.openAndRun)
	tim.start()
	app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
	rt.tearDown()
