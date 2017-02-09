from flask import Flask, render_template, request, jsonify
import readTemp as rt
import pdb
import threading, time
import schedule

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
	# Don't read the temperature if the but is in the process of adjusting it.
	if not rt.isAdjustingTemp: rt.readTemperature(updateTempVal=1)
	heatValStr = "ON" if rt.heaterVal else "OFF"
	return jsonify(temperatureValue=rt.temperatureVal,heaterValue = heatValStr,targetTemperatureValue=rt.targetTemperatureVal,setTemperatureValue=rt.setTemperatureVal,upTime = GetUptime(),lastMessage=rt.lastMessage)

@app.route("/_getFullData")
def _getFullData():
	print "INIT CALLED"
	rt.setup()
	rt.init()
	return jsonify(setTemperatureValue=rt.setTemperatureVal)

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	uptime = check_output(["uptime"])
	return uptime
	
def showHeartBeat():
	rt.showHeartBeat()
	print "HEARTBEAT"
	tim = threading.Timer(4, showHeartBeat)
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
