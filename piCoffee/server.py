import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

import time, threading
from BaseClasses.baseServer import Server
import logging, json
from BaseClasses import myLogger
from BaseClasses.utils import *
import numpy as np
from BaseClasses.segments import *

# Also this: https://www.raspberrypi.org/documentation/hardware/raspberrypi/spi/README.md
# Pi pin          MAX6675 from https://www.raspberrypi.org/forums/viewtopic.php?p=1065060
 # 6 (GND)  <---> GND
 # 1 (3V3)  <---> VCC
# 23 (SCLK) <---> SCK
# 24 (CE0)  <---> CS
# 21 (MISO) <---> SO
    
# pi.spi_open(0, 1000000, 0)    # CE0, 1Mbps, main SPI
# pi.spi_open(1, 1000000, 0)    # CE1, 1Mbps, main SPI
# pi.spi_open(0, 1000000, 256) # CE0, 1Mbps, auxiliary SPI
# pi.spi_open(1, 1000000, 256) # CE1, 1Mbps, auxiliary SPI
# pi.spi_open(2, 1000000, 256) # CE2, 1Mbps, auxiliary SPI

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

relayGPIO = 10
ledClkGPIO=2
ledDatGPIO=3

class MainServer(Server):
    
    paramFile = 'params.json'
    curTemp = 0
    targetTemp = 190
    heatOn = 0
    histLength = 4
    tempHist = np.zeros(histLength)
    
    def __init__(self):
        myLogger.setLogger('server.log',mode='a',dateFormat="%H:%M:%S",level=logging.WARNING)
        self.logFileName = 'server.log'
        logging.warning('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(relayGPIO, pigpio.OUTPUT)
        self.pi.write(relayGPIO,0)
        self.sensor = self.pi.spi_open(0, 1000000, 0) # CE0 on main SPI
        self.ledDisp = TM1637(clk=ledClkGPIO, dio=ledDatGPIO)
        self.ledDisp.show("INIT")
        self.loadParams()
        self.startMainLoop()

                       
    def __delete__(self):
        print "DELETE"
        self.pi.stop()
        self.saveParams()
    
    def readTemp(self):
        c, d = self.pi.spi_read(self.sensor, 2)
        temp = -1
        if c == 2:
            word = (d[0]<<8) | d[1]
            if (word & 0x8006) == 0: # Bits 15, 2, and 1 should be zero.
                temp = (word >> 3)/4.0
                #print("{:.2f}".format(temp))
            else:
                print("bad reading {:b}".format(word))
        else:
            print("bad reading {:b}".format(word))
        time.sleep(.5)
        return temp

        
    def startMainLoop(self):
        def sendData(str):
            try:
                socketio.emit('currentValues', {'status': str,'curTemp':self.curTemp,'targetTemp':self.targetTemp,
                'time':'Current time: ' + time.ctime(time.time())})
            except:
                pass
        
        def doLoop():
            while 1:
                curTemp = np.mean([self.readTemp() for ii in range(4)])
                if curTemp == -1:
                    logging.error("Error reading temp")
                    time.sleep(1)
                    continue
                self.curTemp = curTemp
                self.tempHist[1:] = self.tempHist[0:-1]
                self.tempHist[0] = self.curTemp
                self.dTemp = (self.tempHist[0]-self.tempHist[-1])/self.histLength if self.tempHist[-1] else 0
                print("T = {:.3f} --- DT = {:.3f}".format(curTemp,self.dTemp))
                
                self.ledDisp.show(" {:.0f}F".format(self.curTemp) if not self.heatOn else "_{:.0f}F".format(self.curTemp))
                sendData("")                    
                time.sleep(1)
        t = threading.Thread(target=doLoop)
        t.daemon = True
        t.start()
                
    def saveParams(self):
        with open(self.paramFile,'w') as f:
            json.dump({'targetTemp':self.targetTemp},f)
    def loadParams(self):
        try:
            with open(self.paramFile) as f:
                D = json.load(f)
                self.targetTemp = D['targetTemp']
        except:
            pass
        


@app.route('/favicon.ico')
def favicon():
    print "FAV ICON"
    return ('', 204)
            
@app.route("/reboot")
def reboot():
    server.reboot()
    return ('', 204)
    
@app.route('/kg')
def kg():
    server.kg()
    return ('', 204)

@app.route('/_init')
def init():
    print "INIT"
    #return(jsonify(threshFactor=server.threshFactor,zapTimeS=server.zapTimeS, log=server.getLog(400)))

# @app.route('/setRatio_<int:param1>')
# def setRatio(param1):
    # server.targetOutV = param1/100.*256
    # return ('', param1)

    # return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    print "/"
    return server.Index()
    
@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1,param2):
    return jsonify(param1=param1,param2=param2)


@socketio.on('Calib')
def Calib(arg1):
    print "CALIBRATE {}".format(arg1['data'])
    #server.calibrate()

@app.route('/log')
def log():
    print "LOG"
    return jsonify(log=server.getLog())

    
server = MainServer()

if __name__ == "__main__":
    socketio.run(app,host='0.0.0.0',port=8080)
    exit(0)
    