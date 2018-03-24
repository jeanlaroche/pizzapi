import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
import time, threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger

outGPIO = 4

app = Flask(__name__)


class Charger(Server):
    
    oscFreqHz = 10000
    def __init__(self):
        myLogger.setLogger('charger.log',mode='a')
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(outGPIO, pigpio.OUTPUT)
        self.pi.set_pull_up_down(outGPIO, pigpio.PUD_UP)
        self.pi.set_PWM_frequency(outGPIO,self.oscFreqHz)
        self.pi.set_PWM_dutycycle(outGPIO,128)
        #self.pi.write(outGPIO,1)

    def setDutyCycle(self,ratio):
        self.pi.set_PWM_dutycycle(outGPIO,int(255*(ratio)))
        
    def glow(self):
        def doGlow():
            while 1:
                for a in range(0,512):
                    if a>=256: a = 511-a
                    charger.setDutyCycle(a/256.)
                    #print('{:.2f}'.format(a/256.))
                    time.sleep(0.002)
        t = threading.Thread(target=doGlow)
        t.daemon = True
        t.start()



@app.route('/favicon.ico')
def favicon():
    return charger.favicon()
            
@app.route("/reboot")
def reboot():
    charger.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    charger.kg()
    return ('', 204)

@app.route('/setRatio_<int:param1>')
def setRatio(param1):
    print "SET RATIO {}".format(param1)
    charger.setDutyCycle(param1/100.)
    return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return charger.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)

charger = Charger()

if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    #charger.glow()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)

    # while 1:
        # a = raw_input('Command ->[]')
        # a = int(a)
        # lc.turnLigthOnOff(abs(a),a>0)

    #charger.setDutyCycle(1)
    while 1:
        a=raw_input('duty->')
        ratio = float(a)
        charger.setDutyCycle(ratio)
    
    