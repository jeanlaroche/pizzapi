import RPi.GPIO as GPIO
from threading import Timer, Thread
import time, os
import Adafruit_DHT
import json
import numpy as np
ON = 0
OFF = 1


class mushroomControl(object):
    sensor      = Adafruit_DHT.DHT22
    sensorPin   = 14
    fanRelayGPIO = 3    # Relay on right looking at AC connectors
    humRelayGPIO = 2    # Relay on left looking at AC connectors
    updatePeriodS = 4   # How often do we read the temp and humidity
    fanOnPeriodMin = 1      # How often does the fan come on, in minutes.
    fanOnLengthS = 15    # How long does it stay on, in minutes
    fanLastOn = 0
    stopNow = 0
    targetHumidity = 60
    curHumidity = 100
    curTemp = 0
    humidityTrigger = 2
    logFile = './log.txt'
    jsonFile = './mushroom.json'
    fanStatus = 0
    humStatus = 0
    logPeriodS = 30

    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.fanRelayGPIO, GPIO.OUT)
        GPIO.setup(self.humRelayGPIO, GPIO.OUT)
        
        GPIO.output(self.fanRelayGPIO,OFF)
        GPIO.output(self.humRelayGPIO,OFF)
        
        self.readJson()
        
        # Temp update thread.
        def updateTemp():
            while self.stopNow == 0:
                self.updateTemp()
                time.sleep(self.updatePeriodS)
        self.updateTempThread = Thread(target=updateTemp, args=(), group=None)
        self.updateTempThread.daemon = True
        self.mprint("Starting temp update thread")
        self.updateTempThread.start()
        
        def fanLoop():
            while self.stopNow == 0:
                self.controlFan()
                time.sleep(1)
        self.fanThread = Thread(target=fanLoop, args=(), group=None)
        self.fanThread.daemon = True
        self.mprint("Starting fan thread")
        self.fanThread.start()

        def humLoop():
            while self.stopNow == 0:
                self.controlHumidity()
                time.sleep(1)
        self.humThread = Thread(target=humLoop, args=(), group=None)
        self.humThread.daemon = True
        self.mprint("Starting hum thread")
        self.humThread.start()
        
        def logLoop():
            while self.stopNow == 0:
                self.logData()
                time.sleep(self.logPeriodS)
        self.logThread = Thread(target=logLoop, args=(), group=None)
        self.logThread.daemon = True
        self.mprint("Starting log thread")
        self.logThread.start()
        
    def controlFan(self):
        now = time.time()
        if now > self.fanLastOn + self.fanOnPeriodMin*60 and self.fanStatus == 0:
            # Turn fan on
            self.mprint("Turning fan on")
            GPIO.output(self.fanRelayGPIO,ON)
            self.fanLastOn = now
            self.fanStatus = 1
        if now > self.fanLastOn + self.fanOnLengthS and self.fanStatus == 1:
            # Turn fan off
            GPIO.output(self.fanRelayGPIO,OFF)            
            self.mprint("Turning fan off")
            self.fanStatus = 0
            
    def controlHumidity(self):
        if self.curHumidity > self.targetHumidity + self.humidityTrigger and self.humStatus == 1:
            # Turn humidifier off
            self.mprint("Turning humidifier off")
            GPIO.output(self.humRelayGPIO,OFF)
            self.humStatus = 0
        if self.curHumidity < self.targetHumidity - self.humidityTrigger and self.humStatus == 0:
            # Turn humidifier on
            self.mprint("Turning humidifier on")
            GPIO.output(self.humRelayGPIO,ON)
            self.humStatus = 1

    def updateTemp(self):
        curHumidity, curTemp = Adafruit_DHT.read_retry(self.sensor, self.sensorPin)
        if curTemp is None or curHumidity >= 100:
            self.mprint("Failed to read temp")
            return
        self.curHumidity = curHumidity
        self.curTemp = np.round(curTemp*1.8 + 32,decimals=2)
        #self.mprint("Temp {:.2f} -- Humidity {:.2f}".format(self.curTemp,curHumidity))

    def mprint(self,this,logit=1):
        import datetime
        date = datetime.datetime.now().strftime('%H:%M:%S')
        msg = date + ' ' + this
        print(msg)
        self.lastMsg = msg
        if logit:
            with open(self.logFile,'a') as fd:
                fd.write(msg+'\n')
                
    def incTargetHumidity(self,inc):
        self.targetHumidity += inc
        self.writeJson()

    def incFanFreqDur(self,incFreqMin=0,incDurS=0):
        self.fanOnPeriodMin += incFreqMin
        self.fanOnPeriodMin = max(.5,self.fanOnPeriodMin)
        self.fanOnPeriodMin = max(self.fanOnPeriodMin,self.fanOnLengthS/60.+.1)
        
        self.fanOnLengthS += incDurS
        self.fanOnLengthS = max(10,self.fanOnLengthS)
        self.fanOnLengthS = min(60*self.fanOnPeriodMin-10,self.fanOnLengthS)
        
        self.fanOnLengthS = np.round(self.fanOnLengthS,decimals=0)
        self.fanOnPeriodMin = np.round(self.fanOnPeriodMin,decimals=1)
        self.writeJson()
        
    def writeJson(self):
        with open(self.jsonFile,'w') as f:
            json.dump({'fanOnPeriodMin':self.fanOnPeriodMin,'fanOnLengthS':self.fanOnLengthS,'targetHumidity':self.targetHumidity},f)
        
    def readJson(self):
        try:
            with open(self.jsonFile,'r') as f:
                A = json.load(f)
                self.fanOnPeriodMin = A['fanOnPeriodMin']
                self.fanOnLengthS = A['fanOnLengthS']
                self.targetHumidity = A['targetHumidity']
        except:
            pass
            
    def logData(self):
        with open(self.logFile,'a') as f:
            f.write("{} Temp {:.2f} -- Humidity {:.2f}\n".format(time.time(),self.curTemp,self.curHumidity))
            
    def getHumidityData(self,pastTimesH):
        with open(self.logFile,'r') as f:
            allLines = f.readlines()
        X = []
        Y = []
        cutoffTime = time.time()-pastTimesH*3600
        for line in allLines:
            if not "Humidity" in line: continue
            thisTime = float(line.split()[0])-cutoffTime
            if thisTime < 0: continue
            Y.append(float(line.split()[-1]))
            X.append(thisTime/3600.)
        return X,Y
            
        
if __name__ == '__main__':
    print("Constructor")
    hc = mushroomControl()
    print("STARTLOOP")
    while 1:
        time.sleep(1)
        