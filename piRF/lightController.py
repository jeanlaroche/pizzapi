import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from _433 import tx
import time
from BaseClasses import baseServer


TX_GPIO = 17
# Codes for our light remote. > 0 means turn on, < 0 means turn off
codesLivRoom = {1:5510451,-1:5510460,2:5510595,-2:5510604,3:5510915,-3:5510924,4:5512451,-4:5512460,5:5518595,-5:5518604}
codesBedRoom = {1:283955,-1:283964,2:284099,-2:284108,3:284419,-3:284428,4:285955,-4:285964,5:292099,-5:292108
}
codes = codesLivRoom
#codes = codesBedRoom

app = Flask(__name__)
log = None

class lightController(baseServer.Server):

    transmitter = None
    pi = None
    
    def __init__(self):
        global log
        super(lightController,self).__init__("rfLights.log")
        log = baseServer.log
        self.pi = pigpio.pi() # Connect to local Pi.
        self.transmitter = tx(self.pi,gpio = TX_GPIO, repeats=6)

    def Index(self):
        return jsonify(imAlive="I am alive")
        
    def turnLigthOnOff(self, lightNum, onOff):
        if lightNum == 6:
            for ii in range(1,6):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        code = codes[lightNum] if onOff == 1 else codes[-lightNum]
        self.transmitter.send(code)
        log.info('Turning light %d %d',lightNum,onOff)
        
@app.route('/favicon.ico')
def favicon():
    return lc.favicon()
            
@app.route("/reboot")
def reboot():
    return lc.reboot()

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return lc.Index()

@app.route("/allOff")
def allOff():
    lc.turnLigthOnOff(6,-1)
    return jsonify(allOff='allOff')

@app.route("/allOn")
def allOn():
    lc.turnLigthOnOff(6,1)
    return jsonify(allOn='allOn')

@app.route("/lightOnOff/<int:light_id>/<int:on_off>")
def lightOnOff(light_id,on_off):
    lc.turnLigthOnOff(light_id,on_off)
    return jsonify(light_id=light_id,on_off=on_off)
    
lc = lightController()


if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    
    while 1:
        a = raw_input('Command ->[]')
        a = int(a)
        lc.turnLigthOnOff(abs(a),a>0)
        
