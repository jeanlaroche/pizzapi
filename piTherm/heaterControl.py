import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time
import pygame

class heaterControl(object):
    roomTemp = 70
    targetTemp = 70
    updatePeriodS = 2
    tempHistoryLengthS = 120
    relayGPIO = 17
    stopNow = 0
    buttonPressed = -1

    tempHistory = []
    _targetTemp = 0

    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)
        def onTouch(s,down):
            self.onTouch(s,down)
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

    def onTempOff(self):
        print "TEMP OFF"

    def onRun(self):
        print "RUN"

    def onHold(self):
        print "HOLD"

    def onTouch(self,s,down):
        # print s.x,s.y
        if down:
            self.buttonPressed = self.display.findHit(s)
            if s.x < 30 and s.y < 30: self.close()
        if not down and self.buttonPressed > -1:
            print "Heater control button: {}".format(self.buttonPressed)
            if self.buttonPressed == 0: self.onTempOff()
            if self.buttonPressed == 1: self.onRun()
            if self.buttonPressed == 2: self.onHold()

        if self.buttonPressed == -1:
            if down:
                dx,dy=s.x-self.display.firstDownPos[0],s.y-self.display.firstDownPos[1]
                self._targetTemp = self.targetTemp - dy /10
                print dy,self._targetTemp
                #self.draw(doTarget=self._targetTemp)
                # import pdb
                # pdb.set_trace()
                self.display.screen.fill(dc.black,rect=pygame.Rect(0,0,200,20))
                self.display.make_label("Target {}".format(self._targetTemp),0,0,40,dc.red)
            else:
                self.targetTemp = self._targetTemp
                self.draw()

    def draw(self,doTarget=0):
        self.display.screen.fill(dc.black)
        buttX=80
        buttY=50
        margin=10
        startX = margin
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, dc.green)
        startX += buttX+margin
        self.display.make_button("Run",startX,self.display.ySize-buttY-margin, buttX, buttY, dc.green)
        startX += buttX+margin
        self.display.make_button("Hold",startX,self.display.ySize-buttY-margin, buttX, buttY, dc.green)
        if not doTarget:
            self.display.make_circle("{:.0f}".format(round(self.roomTemp)), 120, 120, 100, dc.red)
        else:
            self.display.make_circle("{:.0f}".format(round(doTarget)), 120, 120, 100, dc.red)
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