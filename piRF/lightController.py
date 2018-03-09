import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from _433 import tx
import time, threading
from BaseClasses import baseServer


TX_GPIO = 17
# Codes for our light remote. > 0 means turn on, < 0 means turn off
codesLivRoom = {1:5510451,-1:5510460,2:5510595,-2:5510604,3:5510915,-3:5510924,4:5512451,-4:5512460,5:5518595,-5:5518604}
codesBedRoom = {6:283955,-6:283964,7:284099,-7:284108,8:284419,-8:284428,9:285955,-9:285964,10:292099,-10:292108}
codesFamRoom = {11:4461875,-11:4461884,12:4462019,-12:4462028,13:4462339,-13:4462348,14:4463875,-14:4463884,15:4470019,-15:4470028}

codes = codesLivRoom
codes.update(codesBedRoom)
codes.update(codesFamRoom)
#codes = codesBedRoom

app = Flask(__name__)
log = None

class lightController(baseServer.Server):

    transmitter = None
    pi = None
    
    lightOffHour = 23
    lightOffMin = 30
    canTurnOff = 1
    
    def __init__(self):
        global log
        super(lightController,self).__init__("rfLights.log")
        log = baseServer.log
        self.pi = pigpio.pi() # Connect to local Pi.
        self.transmitter = tx(self.pi,gpio = TX_GPIO, repeats=12)
        
        def timerLoop():
            while 1:
                try:
                    locTime = time.localtime()
                    if locTime.tm_hour == self.lightOffHour and locTime.tm_min == self.lightOffMin and self.canTurnOff:
                        log.info('Timer turn lights off')
                        self.turnLigthOnOff(100,0)
                        self.canTurnOff = 0
                    if locTime.tm_hour == (self.lightOffHour + 1 )%24: self.canTurnOff = 1
                    time.sleep(1)
                except Exception as e:
                    self.error('Exception in timer: %s',e)
        
        log.info('Starting timer thread')
        self.timerThread = threading.Thread(target=timerLoop)
        self.timerThread.daemon = True
        self.timerThread.start()

    def Index(self):
        return super(lightController,self).Index("index.html")
        # return jsonify(imAlive="I am alive")
        
    def turnLigthOnOff(self, lightNum, onOff):
        if lightNum == 100:
            for ii in range(1,6):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        if lightNum == 101:
            for ii in range(6,11):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        if lightNum == 102:
            for ii in range(11,16):
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

@app.route("/lightOnOff/<int:light_id>/<int:on_off>")
def lightOnOff(light_id,on_off):
    lc.turnLigthOnOff(light_id,on_off)
    return ('', 204)
    
lc = lightController()


if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    
    while 1:
        a = raw_input('Command ->[]')
        a = int(a)
        lc.turnLigthOnOff(abs(a),a>0)
        
