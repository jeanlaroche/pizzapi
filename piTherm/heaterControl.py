import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time
import pygame
import Adafruit_DHT


class heaterControl(object):
    roomTemp = 0
    targetTemp = 70
    updatePeriodS = 2
    tempHistoryLengthS = 120
    relayGPIO = 17
    stopNow = 0
    buttonPressed = -1

    tempHistory = []
    _targetTemp = 0
    sensor = Adafruit_DHT.DHT11
    sensorPin = 14
    celcius = 0

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
        Timer(self.updatePeriodS, updateTemp, ()).start()

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
            self.drawButtons(highlightButton=self.buttonPressed)
            def foo():
                self.drawButtons()
            Timer(.5, foo, ()).start()
            if self.buttonPressed == 0: self.onTempOff()
            if self.buttonPressed == 1: self.onRun()
            if self.buttonPressed == 2: self.onHold()

        if self.buttonPressed == -1:
            if down:
                dx,dy=s.x-self.display.firstDownPos[0],s.y-self.display.firstDownPos[1]
                self._targetTemp = self.targetTemp - dy /20
                print dy,self._targetTemp
                self.showTarget(self._targetTemp)
            else:
                self.targetTemp = self._targetTemp
                self.draw()

    def showTarget(self,target):
        self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 0, 200, 40))
        self.display.make_label("Target {}F".format(target), self.display.xSize / 2, 0, 40, dc.red)

    def drawButtons(self,highlightButton=-1):
        buttX=80
        buttY=50
        margin=10
        startX = margin
        colors = [dc.green]*3
        if highlightButton > -1: colors[highlightButton] = dc.red
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[0])
        startX += buttX+margin
        self.display.make_button("Run",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[1])
        startX += buttX+margin
        self.display.make_button("Hold",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[2])

    def showRoomTemp(self,):
        X,Y,R=120,120,100
        self.display.screen.fill(dc.black, rect=pygame.Rect(X-R, Y-R, 2*R, 2*R))
        self.display.make_circle("{:.0f}".format((self.roomTemp)), X, Y, R, dc.red)

    def draw(self,highlightButton=-1):
        self.display.screen.fill(dc.black)
        self.drawButtons(highlightButton)
        self.showRoomTemp()
        self.showTarget(self.targetTemp)
        self.display.update()

    def updateTemp(self):
        humidity, curTemp = Adafruit_DHT.read_retry(self.sensor, self.sensorPin)
        if curTemp is None or humidity >= 100:
            print "Failed to read temp"
            return
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        prevRoomTemp = round(self.roomTemp)
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        if not self.celcius: self.roomTemp = self.roomTemp * 1.8 + 32
        print "Room temp {} {} {} data points. Hum: {}".format(curTemp,self.roomTemp,len(self.tempHistory[self.tempHistory>0]),humidity)
        if round(self.roomTemp) != prevRoomTemp or 1:
            self.showRoomTemp()

    def startLoop(self):
        self.stopNow = 0
        self.draw()
        while self.stopNow == 0:
            time.sleep(1)

if __name__ == '__main__':
    hc = heaterControl()
    hc.startLoop()
