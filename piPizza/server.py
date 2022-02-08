from BaseClasses.baseServer import Server
from ReadTemps import Temps
from UI import UI
import pigpio
import time
from datetime import datetime

from BaseClasses.utils import runThreaded, readJsonFile, writeJsonFile
from flask import Flask, jsonify

app = Flask(__name__)

TopRelay    = 14
BotRelay    = 15

class PID():
    # Class that implements the PID controller.
    targetTemp = 1
    currentTemp = 0
    dTemp = 0
    outVal = 0
    lastTime = 0
    isOn = 0

    def __init__(self):
        pass

    def getValue(self, currentTemp):
        # Returns the pwm value given the current temp.
        thisTime = time.time()
        self.dTemp = 0 if self.lastTime == 0 else (currentTemp - self.currentTemp) / (thisTime - self.lastTime)
        self.currentTemp = currentTemp
        self.lastTime = thisTime
        self.p = 10   # Proportional factor
        self.d = 1  # Differential factor
        outVal = self.p * (self.targetTemp - self.currentTemp)/self.targetTemp + self.d * self.dTemp / self.targetTemp
        self.outVal = max(0,min(1,outVal)) if self.isOn else 0
        return self.outVal



class PizzaServer(Server):
    topTemp = 0
    botTemp = 0
    ambientTemp = 0
    isOn = 0
    tempHistT = []
    tempHistTop = []
    tempHistBot = []
    jsonFileName = 'params.json'
    lastHistTime = 0
    maxPWM = 0.9
    topPWM = 0
    botPWM = 0

    def __init__(self):
        super().__init__()
        self.Temps = Temps()
        self.topPID = PID()
        self.botPID = PID()
        self.UI = UI(self)
        self.pi = pigpio.pi()  # Connect to local Pi.
        self.pi.set_mode(TopRelay, pigpio.OUTPUT)
        self.pi.set_mode(BotRelay, pigpio.OUTPUT)
        self.pi.write(TopRelay, 0)
        self.pi.write(BotRelay, 0)
        data = readJsonFile(self.jsonFileName)
        try:
            self.topPID.targetTemp = data.get('topTargetTemp',20)
            self.botPID.targetTemp = data.get('botTargetTemp',20)
            self.maxPWM = data.get('maxPWM',1)
        except:
            print("Error while loading json")
        self.saveJson()
        runThreaded(self.processLoop)

    def __delete__(self):
        self.pi.stop()

    def saveJson(self):
        writeJsonFile(self.jsonFileName,{'topTargetTemp':self.topPID.targetTemp,'botTargetTemp':self.botPID.targetTemp,'maxPWM':self.maxPWM})
        self.UI.setTargetTemps(self.topPID.targetTemp,self.botPID.targetTemp)

    def onOff(self):
        self.isOn = 1-self.isOn
        print("ISON: ",self.isOn)

    def incTemp(self,p1,p2):
        if p1 == 0: self.topPID.targetTemp += p2
        if p1 == 1: self.botPID.targetTemp += p2
        server.saveJson()

    def processLoop(self):
        while 1:
            self.topTemp,self.botTemp,self.ambientTemp = self.Temps.getTemps()
            self.topPID.isOn = self.isOn
            self.botPID.isOn = self.isOn
            self.topPWM = self.topPID.getValue(self.topTemp)
            self.botPWM = self.botPID.getValue(self.botTemp)
            self.topPWM,self.botPWM = min(self.topPWM,self.maxPWM),min(self.botPWM,self.maxPWM)
            self.UI.setCurTemps(self.topTemp,self.botTemp)
            # print(f"TopVal {topVal:.2f} BotVal {botVal:.2f}")

            if time.time() - self.lastHistTime > 60 or round(self.topTemp) != self.tempHistTop[-1]\
                    or round(self.botTemp) != self.tempHistBot[-1]:
                self.lastHistTime = time.time()
                curTime = datetime.now()
                self.tempHistT.append(curTime.isoformat())
                self.tempHistTop.append(round(self.topTemp))
                self.tempHistBot.append(round(self.botTemp))
            time.sleep(0.5)

@app.route('/favicon.ico')
def favicon():
    return server.favicon()


@app.route("/reboot")
def reboot():
    server.reboot()
    return ('', 204)


@app.route('/kg')
def kg():
    server.kg()
    return ('', 204)


# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return server.Index()

def _onOff():
    return "OVEN IS ON" if server.isOn else "OVEN IS OFF"

@app.route("/getTemps")
def getTemps():
    return jsonify(topTemp = server.topTemp,botTemp=server.botTemp,topTarget=server.topPID.targetTemp,
                   botTarget=server.botPID.targetTemp,ambientTemp=server.ambientTemp,onOff = _onOff(),
                   topPWM=round(server.topPWM,2),botPWM=round(server.botPWM,2),
                   dataLen = len(server.tempHistT),time=time.ctime(time.time()))

@app.route("/getTempHist")
def getTempHist():
    return jsonify(xVals=server.tempHistT,yValsTop=server.tempHistTop,yValsBot=server.tempHistBot)


@app.route("/onOff")
def onOff():
    server.onOff()
    return jsonify(onOff = _onOff())



@app.route("/incTopTemp/<int(signed=True):param1>")
def incTopTemp(param1):
    print("incTopTemp",param1)
    server.topPID.targetTemp += param1
    server.saveJson()
    return jsonify(topTarget=server.topPID.targetTemp)

@app.route("/incBotTemp/<int(signed=True):param1>")
def incBotTemp(param1):
    server.botPID.targetTemp += param1
    server.saveJson()
    return jsonify(botTarget=server.botPID.targetTemp)


@app.route("/funcName/<int:param1>/<int:param2>")
def funcName(param1, param2):
    return jsonify(param1=param1, param2=param2)

if __name__ == "__main__":
    server = PizzaServer()
    print("Go to http://192.168.1.129:8080")

    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    def foo():
        app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)

    runThreaded(foo)
    server.UI.mainLoop()
