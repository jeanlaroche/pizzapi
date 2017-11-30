#!/usr/bin/python
import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time
import pygame
import Adafruit_DHT
import schedule


class heaterControl(object):
    roomTemp = 0
    targetTemp = 70
    updatePeriodS = 4
    tempHistoryLengthS = 120
    relayGPIO = 17
    stopNow = 0
    buttonPressed = -1
    humidity = 0
    waitForUp = 0

    tempHistory = []
    _targetTemp = 0
    sensor = Adafruit_DHT.DHT11
    sensorPin = 14
    celcius = 0
    holding = 0
    heaterOn = 0
    heaterToggleDeltaTemp = 1
    heaterToggleCount = 0
    heaterToggleMinCount = 3

    def __init__(self,doStart=1):
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
        if doStart: Timer(self.updatePeriodS, updateTemp, ()).start()

        def eventLoop():
            self.display.eventLoop()
        self.touchThread = Thread(target=eventLoop, args=(), group=None)
        self.touchThread.daemon = True
        if doStart: self.touchThread.start()
        self.draw()
        # Start schedule.
        def doSchedule():
            schedule.openAndRun(self)
        self.scheduleThread = Thread(target=doSchedule, args=(), group=None)
        self.scheduleThread.daemon = True
        if doStart: self.scheduleThread.start()
        
    def controlHeater(self):
        # Todo: maybe we need a maximum length of time the furnace can be on.
        if self.roomTemp <= self.targetTemp - self.heaterToggleDeltaTemp: 
            self.heaterToggleCount += 1
            if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterOn = 1
        elif self.roomTemp >= self.targetTemp + self.heaterToggleDeltaTemp: 
            self.heaterToggleCount += 1
            if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterOn = 0
        else:
            self.heaterToggleCount = 0
        print "Toggle count {}".format(self.heaterToggleCount)
        if self.heaterOn: print "HEATER ON" 
        else: print "HEATER OFF"
        if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterToggleCount = self.heaterToggleMinCount

    def mprint(self,this):
        print(this)

    def close(self):
        print "Closing Heater Control"
        self.stopNow = 1
        self.display.close()

    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        self.heaterToggleCount = 0
        self.showTarget(self.targetTemp)
        
    def onTempOff(self):
        self.setTargetTemp(50)
        print "TEMP OFF"

    def onRun(self):
        self.holding = 0
        schedule.redoSchedule()
        print "RUN"

    def onHold(self):
        self.holding = 1-self.holding
        self.drawButtons()
        print "HOLD"

    def incTargetTemp(self,inc):
        self.setTargetTemp(self.targetTemp + inc)

    def onTouch(self,s,down):
        # print s.x,s.y
        if down:
            self.buttonPressed = self.display.findHit(s)
            if s.x < 60 and s.y < 60: self.close()
        if down and self.waitForUp: return
        if self.buttonPressed > -1 and down:
            print "Heater control button: {}".format(self.buttonPressed)
            self.drawButtons(highlightButton=self.buttonPressed)
            def foo():
                self.drawButtons()
            Timer(.5, foo, ()).start()
            if self.buttonPressed == 0: self.onTempOff()
            if self.buttonPressed == 1: self.onRun()
            if self.buttonPressed == 2: self.onHold()
            self.waitForUp = 1
        if self.buttonPressed == -1:
            if down:
                if s.y > self.display.ySize/2: self.incTargetTemp(-1)
                else: self.incTargetTemp(1)
            self.waitForUp = 1
            # if down:
                # dx,dy=s.x-self.display.firstDownPos[0],s.y-self.display.firstDownPos[1]
                # self._targetTemp = self.targetTemp - dy /20
                # print dy,self._targetTemp
                # self.showTarget(self._targetTemp)
            # else:
                # self.targetTemp = self._targetTemp
                # #self.draw()
        if not down: self.waitForUp = 0

    def showTarget(self,target):
        self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 0, 200, 40))
        self.display.make_label("Target {}F".format(target), self.display.xSize / 2, 0, 40, dc.nblue)

    def drawButtons(self,highlightButton=-1):
        buttX=80
        buttY=50
        margin=10
        startX = margin
        colors = [dc.nocre]*3
        if highlightButton > -1: colors[highlightButton] = dc.nred
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[0])
        startX += buttX+margin
        self.display.make_button("Run",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[1])
        startX += buttX+margin
        if self.holding: colors[2] = dc.nred
        self.display.make_button("Hold",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[2])

    def showRoomTemp(self,):
        X,Y,R=120,120,100
        self.display.screen.fill(dc.black, rect=pygame.Rect(X-R, Y-R, 2*R, 2*R))
        self.display.make_circle("{:.1f}".format((self.roomTemp)), X, Y, R, dc.nred)
        self.display.make_label("Humidity {}".format(self.humidity),X-64,Y+40,30,dc.nteal)

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
        self.humidity = humidity
        if not self.celcius: self.roomTemp = self.roomTemp * 1.8 + 32
        print "Room temp {} {} {} data points. Hum: {}".format(curTemp,self.roomTemp,len(self.tempHistory[self.tempHistory>0]),humidity)
        if round(self.roomTemp) != prevRoomTemp or 1:
            self.showRoomTemp()
        self.showUptime()
        self.display.make_disk(self.display.xSize-50,self.display.ySize-50,40,dc.nteal if not self.heaterOn else dc.nred)
        self.controlHeater()

    def startLoop(self):
        self.stopNow = 0
        self.draw()
        while self.stopNow == 0:
            time.sleep(1)
            
    def showUptime(self):
        # get uptime from the linux terminal command
        from subprocess import check_output
        import re
        uptime = check_output(["uptime"])
        uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime).strip()
        self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 50, 300, 40))
        self.display.make_label(uptime, self.display.xSize / 2, 50, 20, dc.nblue)

if __name__ == '__main__':
    print "Constructor"
    hc = heaterControl()
    print "Startloop"
    hc.startLoop()
