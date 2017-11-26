import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time

class heaterControl(object):
    roomTemp = 0
    targetTemp = 0
    updatePeriodS = 2
    tempHistoryLengthS = 120
    relayGPIO = 17
    stopNow = 0

    tempHistory = []

    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)
        def onTouch(s):
            self.onTouch(s)
        self.display = dc.displayControl(onTouch)

        def updateTemp():
            self.updateTemp()
            if self.stopNow == 0:
                Timer(self.updatePeriodS, updateTemp, ()).start()
        updateTemp()

        def eventLoop():
            self.display.eventLoop()
        self.touchThread = Thread(target=eventLoop, args=(), group=None)
        self.touchThread.daemon = True
        self.touchThread.start()

    def close(self):
        print "Closing Heater Control"
        self.stopNow = 1
        self.display.close()

    def onTouch(self,s):
        print "Heater control on touch"
        if s.x<30 and s.y < 30:
            self.close()

    def draw(self):
        self.display.screen.fill(dc.black)
        buttX=80
        buttY=50
        margin=10
        startX = margin
        self.display.make_button("On",startX,self.display.ySize-buttY-margin, buttX, buttY, dc.blue)
        startX += buttX+margin
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, dc.blue)
        self.display.make_circle("76", self.display.xSize / 2, self.display.ySize / 2, 100, dc.red)
        self.display.update()

    def updateTemp(self):
        curTemp = 68
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        print "Room temp {} {} data points".format(self.roomTemp,len(self.tempHistory[self.tempHistory>0]))

    def startLoop(self):
        self.stopNow = 0
        self.draw()
        while self.stopNow == 0:
            time.sleep(1)

if __name__ == '__main__':
    hc = heaterControl()
    hc.startLoop()