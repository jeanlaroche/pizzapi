from flask import Flask, render_template, request, jsonify
import readTemp as rt
import pdb

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	return render_template("index.html", uptime=GetUptime())

# Helper function to return a jsonified string with the temp.
def getTargetTempRet():
	targetTemperatureRet = "{:.0f} F".format(rt.targetTemperatureVal)
	return jsonify(targetTemperatureValue=targetTemperatureRet)

@app.route("/_tempUp")
def _tempUp():
	rt.incSetTemperature(1)
	return getTargetTempRet()

@app.route("/_tempDown")
def _tempDown():
	print "TEMP DOWN"
	rt.incSetTemperature(-1)
	return getTargetTempRet()

@app.route("/_getTubStatus")
def _getTubStatus():
	rt.readTemperature()
	tempValRet = "{:.0f} F".format(rt.temperatureVal)
	targetTempValRet = "{:.0f} F".format(rt.targetTemperatureVal)
	setTempValRet = "{:.0f} F".format(rt.setTemperatureVal)
	heatValRet = "ON" if rt.heaterVal else "OFF"
	return jsonify(temperatureValue=tempValRet,heaterValue = heatValRet,targetTemperatureValue=targetTempValRet,setTemperatureValue=setTempValRet,upTime = GetUptime())

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	uptime = check_output(["uptime"])
	return uptime
	
# run the webserver on standard port 80, requires sudo
if __name__ == "__main__":
	# Pins.Init()
	rt.setup()
	app.run(host='0.0.0.0', port=80, debug=True)
	rt.tearDown()