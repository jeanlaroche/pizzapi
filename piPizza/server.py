#! /usr/bin/python3
from BaseClasses.baseServer import Server
from ReadTemps import Temps
from UI import UI
import pigpio
import time
import subprocess
import re
from datetime import datetime
import os
from collections import deque

from BaseClasses.utils import runThreaded, saveVarsToJson, readVarsFromJson
from flask import Flask, jsonify

__version__ = "1.0.2 (2/10/2022)"

app = Flask(__name__)

TopRelay    = 14
BotRelay    = 15

class PID():
    # Class that implements the PID controller.
    targetTemp = 20
    currentTemp = 0
    # PID Parameters.
    p = 10              # Proportional factor. 100 means that a 1% delta between target and current -> full PWM.
    d = 1               # Differential factor. 100 means that a 1% delta per second between target and current -> full PWM
    # Update parameters
    smoothPeriodS = 20  # The dynamics (slopes) are computed over this duration.
    dTemp = 0
    outVal = 0
    lastTime = 0
    isOn = 0
    timeToTarget = ""

    def __init__(self,updatePeriodS):
        # updatePeriodS controls how often we update the output pwm value. If we update every second and
        # want a smooth period of 10s, we need to keep the 10 past values.
        dqLen = int(self.smoothPeriodS / updatePeriodS)
        self.updatePeriodS = updatePeriodS
        self.lastTimes = deque(maxlen=dqLen)
        self.lastTemps = deque(maxlen=dqLen)
        self.timeToTarget = "Wait..."
        pass

    def getValue(self, currentTemp):
        # Returns the pwm value given the current temp.
        self.currentTemp = currentTemp
        thisTime = time.time()
        # Don't run unless updatePeriodS seconds have elapsed.
        if len(self.lastTimes) and thisTime - self.lastTimes[-1] < self.updatePeriodS: return self.outVal
        # Append time and temperature to our deque, we append on the right ([-1]) and read on the left
        self.lastTimes.append(thisTime)
        self.lastTemps.append(currentTemp)
        # We need the deque to be full to compute the dynamics.
        if len(self.lastTimes) < self.lastTimes.maxlen : return self.outVal
        lastTime = self.lastTimes[0]
        lastTemp = self.lastTemps[0]
        self.dTemp = (currentTemp - lastTemp) / (thisTime - lastTime)
        if self.targetTemp:
            outVal = self.p * (self.targetTemp - self.currentTemp)/self.targetTemp - self.d * self.dTemp / self.targetTemp
        else:
            outVal = 0
        self.outVal = max(0,min(1,outVal)) if self.isOn else 0
        self.timeToTarget = self.getTimeToTarget()
        return self.outVal

    def getTimeToTarget(self):
        if abs(self.targetTemp-self.currentTemp) < 0.02*self.targetTemp: return "At temp"
        if self.dTemp == 0: return "Inf"
        ttt = (self.targetTemp - self.currentTemp)/self.dTemp
        if ttt < 0 : return "Inf"
        if ttt < 60: return f"{ttt:.0f} sec"
        if ttt < 3600: return f"{ttt/60:.0f} min"
        if ttt < 3600*2: return "> 1 hour"
        return "Inf"


class PizzaServer(Server):
    pidCallPeriodS     =    2                                     # How often we call the PID to get new PWM values.
    topTemp            =    0                                     #
    botTemp            =    0                                     #
    ambientTemp        =    0                                     #
    isOn               =    0                                     # Flag to indicate whether we're on or off
    tempHistT          =    []                                    # Histories of temps, this is the time values
    tempHistTop        =    []                                    #
    tempHistBot        =    []                                    #
    jsonFileName       =    '/home/pi/piPizza/params.json'        #
    topMaxPWM          =    0.9                                   #
    botMaxPWM          =    0.9                                   #
    topPWM             =    0                                     #
    botPWM             =    0                                     #
    dirty              =    1                                     # Flag indicating some values have changed.
    stopUI             =    0                                     # Flag to prevent updaing the UI.
    version            =    __version__                           #

    def __init__(self):
        super().__init__()
        self.Temps = Temps()
        self.topPID = PID(self.pidCallPeriodS)
        self.botPID = PID(self.pidCallPeriodS)
        self.UI = UI(self)
        self.pi = pigpio.pi()  # Connect to local Pi.
        self.pi.set_mode(TopRelay, pigpio.OUTPUT)
        self.pi.set_mode(BotRelay, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(TopRelay, 0)
        self.pi.set_PWM_frequency(BotRelay, 0)
        self.pi.set_PWM_dutycycle(TopRelay, 0)
        self.pi.set_PWM_dutycycle(BotRelay, 0)

        readVarsFromJson(self.jsonFileName,self,"server")
        readVarsFromJson(self.jsonFileName,self.topPID,"topPID")
        readVarsFromJson(self.jsonFileName,self.botPID,"botPID")
        readVarsFromJson(self.jsonFileName,self.UI,"UI")
        self.lastHistTime = 0
        self.isOn = 0
        self.dirty = 1
        self.stopUI = 0
        self.ip = ""

        try:
            A=subprocess.check_output(['/sbin/ifconfig','wlan0']).decode()
            self.ip = re.search('inet\s+(\S*)',A).group(1)
        except:
            pass
        self.UI.finishInit()
        runThreaded(self.processLoop)

    def __delete__(self):
        self.pi.stop()

    def runUpdate(self,restart=0):
        if not restart:
            try:
                A=subprocess.check_output('git pull upstream'.split()).decode()
            except Exception as e:
                print(e)
                A=f"Failed to update: {e}"
                return A,0
            if "Already up to date" in A:
                return "Already up to date, restarting now",1
            else:
                return "Update done, will restart now",1
        else:
            # Kill this process and relaunch it.
            os.system(f'sh -c "kill -9 {os.getpid()} ; /usr/bin/python3 /home/pi/piPizza/server.py"')

    def saveJson(self):
        saveVarsToJson(self.jsonFileName,self,"server")
        saveVarsToJson(self.jsonFileName,self.topPID,"topPID")
        saveVarsToJson(self.jsonFileName,self.botPID,"botPID")
        saveVarsToJson(self.jsonFileName,self.UI,"UI")

    def onOff(self):
        self.isOn = 1-self.isOn
        self.dirty = 1
        print("ISON: ",self.isOn)

    def incTemp(self,p1,p2):
        if p1 == 0: self.topPID.targetTemp += p2
        if p1 == 1: self.botPID.targetTemp += p2
        self.dirty = 1

    def setTemps(self,vals):
        self.topPID.targetTemp,self.botPID.targetTemp = vals
        self.dirty = 1

    def incMaxPWM(self,p1,p2):
        if p1 == 0: self.topMaxPWM += p2
        if p1 == 1: self.botMaxPWM += p2
        self.topMaxPWM = max(0,min(self.topMaxPWM,1))
        self.botMaxPWM = max(0,min(self.botMaxPWM,1))
        self.dirty = 1

    def setPID(self,vals):
        self.topPID.p,self.topPID.d,self.botPID.p,self.botPID.d = vals
        self.dirty = 1

    def setMaxPWM(self,vals):
        self.topMaxPWM, self.botMaxPWM = vals
        self.dirty = 1

    def processLoop(self):
        while 1:
            try:
                # This can happen when the UI is doing something and it should not be interrupted.
                if self.stopUI:
                    time.sleep(.5)
                    continue
                # Get temps from the thermocouples
                self.topTemp,self.botTemp,self.ambientTemp = self.Temps.getTemps()
                self.topPID.isOn,self.botPID.isOn = self.isOn,self.isOn
                # Run the PID to compute the new pwm values
                self.topPWM = self.topPID.getValue(self.topTemp)
                self.botPWM = self.botPID.getValue(self.botTemp)
                self.topPWM,self.botPWM = min(self.topPWM,self.topMaxPWM),min(self.botPWM,self.botMaxPWM)
                # Set the PWM duty cycle on the relays
                self.pi.set_PWM_dutycycle(TopRelay, self.botPWM*self.pi.get_PWM_range(TopRelay))
                self.pi.set_PWM_dutycycle(BotRelay, self.botPWM*self.pi.get_PWM_range(BotRelay))
                # Reflect new temps and pwm on UI
                self.UI.setCurTemps(self.topTemp, self.botTemp, self.topPWM, self.botPWM, self.isOn, self.ambientTemp,
                                    self.topPID.timeToTarget,self.botPID.timeToTarget)
                if self.dirty:
                    self.UI.setTargetTemps(self.topPID.targetTemp, self.botPID.targetTemp)
                    self.UI.setMaxPWM(self.topMaxPWM,self.botMaxPWM)
                    self.saveJson()
                # Keep a memory of the temperature values. Update every 60s or more often if the temp changes.
                if time.time() - self.lastHistTime > 60 or round(self.topTemp) != self.tempHistTop[-1]\
                        or round(self.botTemp) != self.tempHistBot[-1]:
                    self.lastHistTime = time.time()
                    curTime = datetime.now()
                    self.tempHistT.append(curTime.isoformat())
                    self.tempHistTop.append(round(self.topTemp))
                    self.tempHistBot.append(round(self.botTemp))
                self.UI.plotTemps(self.tempHistT,self.tempHistTop,self.tempHistBot)
                curTime = time.localtime()
                # Erase the temp history every night at 1am.
                if len(self.tempHistT) and curTime.tm_hour == 1 and curTime.tm_min == 0:
                    self.tempHistTop,self.tempHistBot,self.tempHistT,self.lastHistTime = [],[],[],0

                self.dirty = 0
            except Exception as e:
                print("Error in loop",e)
            time.sleep(0.2)

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
                   dataLen = len(server.tempHistT),time=time.ctime(time.time()),
                   topTimeToTarget=server.topPID.timeToTarget(),botTimeToTarget=server.botPID.timeToTarget())

@app.route("/getTempHist")
def getTempHist():
    return jsonify(xVals=server.tempHistT,yValsTop=server.tempHistTop,yValsBot=server.tempHistBot)


@app.route("/onOff")
def onOff():
    server.onOff()
    server.dirty = 1
    return jsonify(onOff = _onOff())


@app.route("/incTopTemp/<int(signed=True):param1>")
def incTopTemp(param1):
    print("incTopTemp",param1)
    server.topPID.targetTemp += param1
    server.dirty = 1
    return jsonify(topTarget=server.topPID.targetTemp)

@app.route("/incBotTemp/<int(signed=True):param1>")
def incBotTemp(param1):
    server.botPID.targetTemp += param1
    server.dirty = 1
    return jsonify(botTarget=server.botPID.targetTemp)

# Example of how to pass parameters to a function
# @app.route("/funcName/<int:param1>/<int:param2>")
# def funcName(param1, param2):
#     return jsonify(param1=param1, param2=param2)

if __name__ == "__main__":
    server = PizzaServer()
    print(f"Go to {server.ip}:8080")

    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    def foo():
        app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)

    runThreaded(foo)
    server.UI.mainLoop()
