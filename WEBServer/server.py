from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
	return render_template("index.html", uptime=GetUptime())

# ajax GET call this function to set led state
# depeding on the GET parameter sent
@app.route("/_led")
def _led():
	state = request.args.get('state')
	if state=="on":
		# Pins.LEDon()
		print "Turning led on"
	else:
		# Pins.LEDoff()
		print "Turning led off"
	return ""

# ajax GET call this function periodically to read button state
# the state is sent back as json data
@app.route("/_button")
def _button():
	print "Reading pin"
	state = "pressed"
	# if Pins.ReadButton():
		# state = "pressed"
	# else:
		# state = "not pressed"
	return jsonify(buttonState=state)

def GetUptime():
	# get uptime from the linux terminal command
	from subprocess import check_output
	output = check_output(["uptime"])
	# return only uptime info
	uptime = output[output.find("up"):output.find("user")-5]
	return uptime
	
# run the webserver on standard port 80, requires sudo
if __name__ == "__main__":
	# Pins.Init()
	app.run(host='0.0.0.0', port=80, debug=True)