#!/usr/bin/python
import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time
import pygame
import Adafruit_DHT
import schedule

state_off = 0
state_on = 1
state_on_too_long = 2
stateStr = ['Heater off','Heater on','Heater on too long']

class heaterControl(object):
    roomTemp = 0
    targetTemp = 70
    updatePeriodS = 4
    tempHistoryLengthS = 120
    relayGPIO = 12
    stopNow = 0
    buttonPressed = -1
    humidity = 0
    waitForUp = 0

    tempHistory = []
    _targetTemp = 0
    sensor = Adafruit_DHT.DHT11
    sensorPin = 5
    celcius = 0
    holding = 0
    heaterOn = 0
    heaterToggleDeltaTemp = .5
    heaterToggleCount = 0
    heaterToggleMinCount = 2
    maxContinuousOnTimeMin = 1
    lastTurnOnTime = float('inf')
    state = state_off
    lastMsg = ''

    def __init__(self,doStart=1):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)
        def onTouch(s,down):
            self.onTouch(s,down)
        self.display = dc.displayControl(onTouch)

        # Temp update thread.
        def updateTemp():
            while self.stopNow == 0:
                self.updateTemp()
                time.sleep(self.updatePeriodS)
        self.updateTempThread = Thread(target=updateTemp, args=(), group=None)
        self.updateTempThread.daemon = True
        self.mprint("Starting temp update thread")
        if doStart: self.updateTempThread.start()
        
        # Display event loop thread.
        def eventLoop():
            self.display.eventLoop()
        self.touchThread = Thread(target=eventLoop, args=(), group=None)
        self.touchThread.daemon = True
        self.mprint("Starting display thread")
        if doStart: self.touchThread.start()
        self.draw()
        
        # Schedule thread
        def doSchedule():
            schedule.openAndRun(self)
        self.scheduleThread = Thread(target=doSchedule, args=(), group=None)
        self.scheduleThread.daemon = True
        self.mprint("Starting schedule thread")
        if doStart: self.scheduleThread.start()
        
    def controlHeater(self):
        # Todo: maybe we need a maximum length of time the furnace can be on.
        if self.roomTemp <= self.targetTemp - self.heaterToggleDeltaTemp: 
            self.heaterToggleCount += 1
            if self.heaterToggleCount >= self.heaterToggleMinCount and self.state != state_on_too_long: 
                if self.heaterOn == 0: self.lastTurnOnTime = time.time()
                self.heaterOn = 1
                self.state = state_on
                self.showHeater()
        elif self.roomTemp >= self.targetTemp + self.heaterToggleDeltaTemp: 
            self.heaterToggleCount += 1
            if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterOn = 0
            self.state = state_off
            self.showHeater()
        else:
            self.heaterToggleCount = 0
        #self.mprint("Toggle count {}".format(self.heaterToggleCount))
        if self.heaterOn and time.time()-self.lastTurnOnTime > self.maxContinuousOnTimeMin*60:
            self.heaterOn = 0
            self.state = state_on_too_long
        self.mprint("{} Last turn on time: {:.0f}s ago".format(stateStr[self.state],time.time()-self.lastTurnOnTime)),
        # self.mprint(" Last turn on time: {:.0f}s ago".format(time.time()-self.lastTurnOnTime))
        if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterToggleCount = self.heaterToggleMinCount
        GPIO.output(self.relayGPIO,self.heaterOn)

    def mprint(self,this):
        print(this)
        self.lastMsg = this

    def close(self):
        self.mprint("Closing Heater Control")
        GPIO.output(self.relayGPIO,0)
        self.stopNow = 1
        self.display.close()

    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        self.heaterToggleCount = 0
        self.showTarget(self.targetTemp)
        
    def onTempOff(self):
        self.setTargetTemp(50)
        self.mprint("TEMP OFF")

    def onRun(self):
        self.holding = 0
        schedule.redoSchedule()
        self.mprint("RUN")

    def onHold(self):
        self.holding = 1-self.holding
        self.drawButtons()
        self.mprint("HOLD")

    def incTargetTemp(self,inc):
        self.setTargetTemp(self.targetTemp + inc)

    def onTouch(self,s,down):
        # print s.x,s.y
        if down:
            self.buttonPressed = self.display.findHit(s)
            if s.x < 60 and s.y < 60: self.close()
        if down and self.waitForUp: return
        if self.buttonPressed > -1 and down:
            self.mprint("Heater control button: {}".format(self.buttonPressed))
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
                inc = 5 if s.x > self.display.xSize - 50 else 1
                if s.y > self.display.ySize/2: self.incTargetTemp(-inc)
                else: self.incTargetTemp(inc)
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

    def showHeater(self):
        self.display.make_disk(self.display.xSize-50,self.display.ySize-50,40,dc.nteal if not self.heaterOn else dc.nred)
        
    def updateTemp(self):
        humidity, curTemp = Adafruit_DHT.read_retry(self.sensor, self.sensorPin)
        if curTemp is None or humidity >= 100:
            self.mprint("Failed to read temp")
            return
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        prevRoomTemp = round(self.roomTemp)
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        self.humidity = humidity
        if not self.celcius: self.roomTemp = self.roomTemp * 1.8 + 32
        #self.mprint("Room temp {} {} {} data points. Hum: {}".format(curTemp,self.roomTemp,len(self.tempHistory[self.tempHistory>0]),humidity))
        print("Room temp {} {} {} data points. Hum: {}".format(curTemp,self.roomTemp,len(self.tempHistory[self.tempHistory>0]),humidity))
        if round(self.roomTemp) != prevRoomTemp or 1:
            self.showRoomTemp()
        self.showUptime()
        self.showHeater()
        self.controlHeater()
        schedule.logHeaterUse()

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
        #self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 70, 300, 40))
        #self.display.make_label(self.lastMsg, self.display.xSize / 2, 70, 20, dc.nblue)
        self.display.screen.fill(dc.black, rect=pygame.Rect(0,self.display.ySize -20, 500, 40))
        self.display.make_label(self.lastMsg, 0, self.display.ySize -18, 20, dc.nblue)

if __name__ == '__main__':
    try:
        print("Constructor")
        hc = heaterControl()
        print("STARTLOOP")
        hc.startLoop()
    except:
        print("STOPPING due to interrupt!")
        hc.close()
        
