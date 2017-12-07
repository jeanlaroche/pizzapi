#!/usr/bin/python
#!/usr/bin/python
import RPi.GPIO as GPIO
import numpy as np
from threading import Timer, Thread
import displayControl as dc
import time, os
import pygame
import Adafruit_DHT
import schedule

state_off = 0
state_on = 1
state_on_too_long = 2
state_pausing = 3
stateStr = ['Heater off','Heater on','Heater on too long','Heater paused']

class heaterControl(object):
    roomTemp = 0
    roomTempAdjust = +2
    targetTemp = 0
    updatePeriodS = 5
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
    maxContinuousOnTimeMin = 45
    timeBeforePauseMin = 15
    pauseLengthMin = 3
    timeBeforeImage = 10
    imageChangePeriodS = 5
    lastIdleTime = 0
    pauseTime = float('inf')
    lastTurnOnForPause = float('inf')
    lastTurnOnTime = float('inf')
    state = state_off
    lastMsg = ''
    imagePath = ''
    allImages = []
    imageDir = '/mnt/mainpc/images'
    imageIdx=0
    lastImageChangeTime = 0
    showImage = 0
    listImagePeriodS = 600
    heaterLogFile = 'heater.log'

    def __init__(self,doStart=1):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)
        schedule.hc = self
        self.lastIdleTime = time.time()
        with open(self.heaterLogFile,'w') as fd:
            pass

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
        # def eventLoop():
            # self.display.eventLoop()
        # self.touchThread = Thread(target=eventLoop, args=(), group=None)
        # self.touchThread.daemon = True
        # self.mprint("Starting display thread")
        # if doStart: self.touchThread.start()
        self.mprint("Starting display thread")
        self.display.startLoop()
        
        # Schedule thread
        def doSchedule():
            schedule.openAndRun(self)
        self.scheduleThread = Thread(target=doSchedule, args=(), group=None)
        self.scheduleThread.daemon = True
        self.mprint("Starting schedule thread")
        
        # List image timer:
        def doListImages():
            self.mprint("TIMER: ListImages",logit=1)
            self.listAllImages()
            if len(self.allImages): Timer(self.listImagePeriodS, doListImages, ()).start()
            else: Timer(30, doListImages, ()).start()
        Timer(10, doListImages, ()).start()
        
        if doStart: self.scheduleThread.start()
        # self.listAllImages()
        # self.updateImage()
        self.mprint("Drawing")
        self.draw()
        self.mprint("Done")
    
    def listAllImages(self):
        self.mprint("Listing images")
        self.allImages = []
        # First of, list all dirs!
        try:
            for ii in range(10):
                self.mprint("TRYING LISTING OF IMAGES")
                os.system('ls {}'.format(self.imageDir))
            for dirpath, dirnames, filenames in os.walk(self.imageDir):
                break
            else: 
                self.mprint("NO IMAGE FOUND")
                return
            np.random.shuffle(dirnames)
            allDirs = dirnames
            #print allDirs
            for dir in allDirs[0:20]:
                for dirpath, dirnames, filenames in os.walk(os.path.join(self.imageDir,dir)):
                    for file in filenames:
                        if not '.jpg' in file: continue
                        self.allImages.append(os.path.join(dirpath,file))
                        # print os.path.join(dirpath,file)
            np.random.shuffle(self.allImages)
        except:
            self.mprint("ERROR DURING SCANNING")
        self.mprint("{} images found".format(len(self.allImages)),logit=1)
        
    def updateImage(self):
        if time.time() - self.lastImageChangeTime > self.imageChangePeriodS and len(self.allImages):
            self.mprint("UPDATING IMAGE")
            # This can fail because we have another thread that could update allImages from under us.
            try:
                if self.imageIdx >= len(self.allImages): self.imageIdx = 0
                self.imagePath = self.allImages[self.imageIdx]
                self.lastImageChangeTime = time.time()
                if self.showImage: self.draw()
            except:
                self.mprint("EXCEPTION DURING IMAGE UPDATE",logit=1)
            self.imageIdx += 1
        
    def updateState(self):
        tempLow = self.roomTemp <= self.targetTemp - self.heaterToggleDeltaTemp 
        tempHigh = self.roomTemp >= self.targetTemp + self.heaterToggleDeltaTemp
        
        if self.state == state_off:
            if tempLow:
                self.heaterToggleCount += 1
                if self.heaterToggleCount >= self.heaterToggleMinCount:
                    self.mprint("Turning heater on",logit=1)
                    # Temp low, turn heater on.
                    self.lastTurnOnTime = time.time()
                    self.lastTurnOnForPause = time.time()
                    self.heaterOn = 1
                    self.heaterToggleCount = 0
                    self.state = state_on
        elif self.state == state_on:
            if tempHigh:
                self.heaterToggleCount += 1
                if self.heaterToggleCount >= self.heaterToggleMinCount: 
                    self.mprint("Turning heater off",logit=1)
                    # Temp reached turn heater off
                    self.heaterOn = 0
                    self.state = state_off
                    self.heaterToggleCount = 0
            if time.time()-self.lastTurnOnTime > self.maxContinuousOnTimeMin*60:
                # Heater on for too long
                self.mprint("Turning heater off, too long",logit=1)
                self.heaterOn = 0
                self.state = state_on_too_long
            if time.time()-self.lastTurnOnForPause  > self.timeBeforePauseMin*60:
                # Take a break
                self.mprint("Turning heater off, Taking a break",logit=1)
                self.heaterOn = 0
                self.state = state_pausing
                self.pauseTime = time.time()
        elif self.state == state_pausing:
            if time.time()-self.pauseTime > self.pauseLengthMin*60:
                self.mprint("Turning heater on, from break",logit=1)
                self.heaterOn = 1
                self.state = state_on
                self.lastTurnOnForPause = time.time()
        elif self.state == state_on_too_long:
            if tempHigh:
                self.mprint("Temp high enough, resuming normal state",logit=1)
                self.state = state_off
        if self.showImage == 0 and time.time() > self.lastIdleTime + self.timeBeforeImage and len(self.allImages):
            self.showImage = 1
            self.draw()
            
        #self.mprint("{} Last turn on time: {:.0f}s ago".format(stateStr[self.state],time.time()-self.lastTurnOnTime))
        #self.mprint("pause time {:.0f}s ago -- last turn on for pause {:.0f}s ago".format(time.time()-self.pauseTime,time.time()-self.lastTurnOnForPause))
        if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterToggleCount = self.heaterToggleMinCount
        GPIO.output(self.relayGPIO,self.heaterOn)
        self.showHeater()
        self.updateImage()
        
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

    def mprint(self,this,logit=0):
        import datetime
        # date = datetime.datetime.now().strftime('%m/%d %Hh%M:%S')
        date = datetime.datetime.now().strftime('%H:%M:%S')
        msg = date + ' ' + this
        print(msg)
        self.lastMsg = msg
        if logit:
            with open(self.heaterLogFile,'a') as fd:
                fd.write(msg+'\n')

    def close(self):
        self.mprint("Closing Heater Control")
        GPIO.output(self.relayGPIO,0)
        self.stopNow = 1
        self.display.close()

    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        if self.targetTemp < 50: self.targetTemp = 50
        if self.targetTemp > 74: self.targetTemp = 74
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
        if self.showImage:
            if down: return
            self.showImage = 0
            self.draw()
            self.showUptime()
        if down:
            self.buttonPressed = self.display.findHit(s)
        else:
            self.lastIdleTime = time.time()
        # if s.x < 20 and s.y < 20: 
            # os.system('sudo reboot now')
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
            if self.buttonPressed == 3: self.setTargetTemp(66)
            self.waitForUp = 1
        if self.buttonPressed == -1:
            if down:
                inc = 5 if s.x > self.display.xSize - 50 else 1
                if s.y > self.display.ySize/2: self.incTargetTemp(-inc)
                else: self.incTargetTemp(inc)
                # self.setTargetTemp(int(65-.1*(s.y-self.display.ySize/2)))
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
        if self.showImage: return
        self.display.make_label("Target {}F".format(target), self.display.xSize / 2, 0, 40, dc.nblue)

    def drawButtons(self,highlightButton=-1):
        if self.showImage: return
        buttX=80
        buttY=50
        margin=10
        startX = margin
        colors = [dc.nocre]*4
        if highlightButton > -1: colors[highlightButton] = dc.nred
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[0])
        startX += buttX+margin
        self.display.make_button("Run",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[1])
        startX += buttX+margin
        if self.holding: colors[2] = dc.nred
        self.display.make_button("Hold",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[2])
        startX += buttX+margin
        self.display.make_button("66F",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[3])

    def showRoomTemp(self,):
        if self.showImage: return
        X,Y,R=120,120,100
        # self.display.screen.fill(dc.black, rect=pygame.Rect(X-R, Y-R, 2*R, 2*R))
        self.display.make_circle("{:.1f}".format((self.roomTemp)), X, Y, R, dc.nred)
        self.display.make_label("Humidity {}".format(self.humidity),X-64,Y+40,30,dc.nteal)

    def draw(self,highlightButton=-1):
        if self.showImage:
            self.display.displayJPEG(self.imagePath)
            self.display.update()
            return
        self.display.screen.fill(dc.black)
        self.drawButtons(highlightButton)
        self.showRoomTemp()
        self.showTarget(self.targetTemp)
        self.display.rectList = [[0,0,self.display.xSize,self.display.ySize]]
        self.display.update()

    def showHeater(self):
        if self.showImage: return
        self.display.make_disk(self.display.xSize-30,self.display.ySize-30,10,dc.nteal if not self.heaterOn else dc.nred)
        
    def updateTemp(self):
        humidity, curTemp = Adafruit_DHT.read_retry(self.sensor, self.sensorPin)
        if curTemp is None or humidity >= 100:
            self.mprint("Failed to read temp")
            return
        curTemp += self.roomTempAdjust
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        prevRoomTemp = round(self.roomTemp)
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        self.humidity = humidity
        if not self.celcius: self.roomTemp = self.roomTemp * 1.8 + 32
        self.mprint("State: {} -- Room temp {} {} {} data points. Hum: {}".format(stateStr[self.state],curTemp,self.roomTemp,len(self.tempHistory[self.tempHistory>0]),humidity))
        if round(self.roomTemp) != prevRoomTemp or 1:
            self.showRoomTemp()
        self.showUptime()
        self.showHeater()
        #self.controlHeater()
        self.updateState()
        self.printQueue()
        schedule.logHeaterUse()
        
    def printQueue(self):
        with open('queue.txt','w') as fd:
            for val in self.tempHistory:
                fd.write("{} ".format(val))

    def startLoop(self):
        self.stopNow = 0
        while self.stopNow == 0:
            time.sleep(1)
                    
    def showUptime(self):
        if self.showImage: return
        # get uptime from the linux terminal command
        from subprocess import check_output
        import re
        uptime = check_output(["uptime"])
        uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime).strip()
        # self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 50, 300, 40))
        self.display.make_label(uptime, self.display.xSize / 2, 50, 20, dc.nblue)
        #self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 70, 300, 40))
        #self.display.make_label(self.lastMsg, self.display.xSize / 2, 70, 20, dc.nblue)
        #self.display.screen.fill(dc.black, rect=pygame.Rect(0,self.display.ySize -20, 500, 40))
        self.display.make_label(self.lastMsg, 0, self.display.ySize -18, 20, dc.nblue, fullLine=1)
        
    def grabLog(self):
        with open('heater.log','r') as f:
            allLines = f.readlines()
            return allLines[-1:-30:-1]
        return []


if __name__ == '__main__':
    print("Constructor")
    hc = heaterControl()
    print("STARTLOOP")
    hc.startLoop()
        
