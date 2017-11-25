import RPi.GPIO as GPIO
import numpy as np
from threading import Timer

class heaterControl(object):
    roomTemp = 0
    targetTemp = 0
    updatePeriodS = 2
    tempHistoryLengthS = 120
    relayGPIO = 17

    tempHistory = []

    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)

        def updateTemp():
            self.updateTemp()
            Timer(self.updatePeriodS, updateTemp, ()).start()

        updateTemp()

    def updateTemp(self):
        curTemp = 68
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        print "Room temp {} {} data points".format(self.roomTemp,len(self.tempHistory[self.tempHistory>0]))
