from flask import Flask, render_template, request, jsonify

# See this: http://electronicsbyexamples.blogspot.com/2014/02/raspberry-pi-control-from-mobile-device.html

setTemperatureVal=99

app = Flask(__name__)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	return render_template("index.html", uptime=GetUptime())

# Helper function to return a jsonified string with the temp.
def getSetTempRet():
	global setTemperatureVal
	setTemperatureRet = "{:.0f} F".format(setTemperatureVal)
	return jsonify(setTemperatureValue=setTemperatureRet)

@app.route("/_tempUp")
def _tempUp():
	print "TEMP UP"
	global setTemperatureVal
	setTemperatureVal = setTemperatureVal+1
	return getSetTempRet()

@app.route("/_tempDown")
def _tempDown():
	print "TEMP DOWN"
	global setTemperatureVal
	setTemperatureVal = setTemperatureVal-1
	return getSetTempRet()

@app.route("/_getTubStatus")
def _getTubStatus():
	global setTemperatureVal
	temperatureVal = "102 F"
	heaterVal = "OFF"
	setTemperatureRet = "{:.0f} F".format(setTemperatureVal)
	return jsonify(temperatureValue=temperatureVal,heaterValue = heaterVal,setTemperatureValue=setTemperatureRet,upTime = GetUptime())

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	uptime = check_output(["uptime"])
	return uptime
	
# run the webserver on standard port 80, requires sudo
if __name__ == "__main__":
	# Pins.Init()
	app.run(host='0.0.0.0', port=80, debug=True)