from flask import Flask, render_template, request, jsonify
import readTemp as rt
import pdb

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html



app = Flask(__name__)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	return render_template("index.html", uptime=GetUptime())

@app.route("/_tempUp")
def _tempUp():
	rt.selfTestNoBlock()
	# rt.incSetTemperature(1)
	# rt.pressTempAdjust()
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_tempDown")
def _tempDown():
	# rt.incSetTemperature(-1)
	return jsonify(targetTemperatureValue=rt.targetTemperatureVal)

@app.route("/_getTubStatus")
def _getTubStatus():
	# Don't read the temperature if the but is in the process of adjusting it.
	if not rt.isAdjustingTemp: rt.readTemperature()
	heatValStr = "ON" if rt.heaterVal else "OFF"
	return jsonify(temperatureValue=rt.temperatureVal,heaterValue = heatValStr,targetTemperatureValue=rt.targetTemperatureVal,setTemperatureValue=rt.setTemperatureVal,upTime = GetUptime(),lastMessage=rt.lastMessage)

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