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
    fanOnLengthMin = 0.2    # How long does it stay on, in minutes
    fanLastOn = 0
    stopNow = 0
    targetHumidity = 60
    curHumidity = 100
    humidityTrigger = 2
    logFile = './log.txt'
    fanStatus = 0
    humStatus = 0

    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.fanRelayGPIO, GPIO.OUT)
        GPIO.setup(self.humRelayGPIO, GPIO.OUT)
        
        GPIO.output(self.fanRelayGPIO,OFF)
        GPIO.output(self.humRelayGPIO,OFF)
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
        
    def controlFan(self):
        now = time.time()
        if now > self.fanLastOn + self.fanOnPeriodMin*60 and self.fanStatus == 0:
            # Turn fan on
            self.mprint("Turning fan on")
            GPIO.output(self.fanRelayGPIO,ON)
            self.fanLastOn = now
            self.fanStatus = 1
        if now > self.fanLastOn + self.fanOnLengthMin * 60 and self.fanStatus == 1:
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
        self.mprint("Temp {:.2f} -- Humidity {:.2f}".format(self.curTemp,curHumidity))

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
        
if __name__ == '__main__':
    print("Constructor")
    hc = mushroomControl()
    print("STARTLOOP")
    while 1:
        time.sleep(1)
        