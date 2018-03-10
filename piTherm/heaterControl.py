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
import json
import urllib2
from BaseClasses import myLogger
from hotTubControl import HotTubControl
import logging

state_off = 0
state_on = 1
state_on_too_long = 2
state_pausing = 3
stateStr = ['Heater off','Heater on','Heater on too long','Heater paused']

class heaterControl(object):
    roomTemp = 0
    roomTempAdjust = 0
    outsideTemp = 0
    maxAirTemp = 0
    minAirTemp = 0
    outsideHum = 0
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
    sensor = Adafruit_DHT.DHT22
    sensorPin = 5
    celcius = 0
    holding = 0
    vacation = 0
    heaterOn = 0
    heaterToggleDeltaTemp = .25
    heaterToggleCount = 0
    heaterToggleMinCount = 2
    maxContinuousOnTimeMin = 70
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
    showHotTub = 0
    listImagePeriodS = 600
    heaterLogFile = 'heater.log'
    statusFile = 'heater.json'
    lightOn = 0

    def __init__(self,doStart=1):
        # Init GPIO
        # global log
        # LL = myLogger.myLogger(self.heaterLogFile,mode='w',format='%(asctime)s -- %(levelname)s: %(message)s')
        # log = LL.getLogger()
        # self.log = log
        myLogger.setLogger(self.heaterLogFile,mode='w',format='%(asctime)s -- %(levelname)s: %(message)s')
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayGPIO, GPIO.OUT)
        self.tempHistory = np.zeros(self.tempHistoryLengthS/self.updatePeriodS)
        schedule.hc = self
        self.lastIdleTime = time.time()
        
        def onTouch(s,down):
            self.onTouch(s,down)
        self.display = dc.displayControl(onTouch,self)
        
        logging.info('Create hottub control')
        self.hotTubControl = HotTubControl(self.display,self)
        self.hotTubControl.getTubStatus()

        # Read the status file if there's one.
        with open(self.statusFile,'r') as f:
            try:
                jsonStat = json.load(f)
                if 'holding' in jsonStat and jsonStat['holding']:
                    self.holding = 1
                    self.setTargetTemp(jsonStat['targetTemp'])
                self.vacation = jsonStat['vacation']
                schedule.vacation = self.vacation
                logging.info("jsonStat read: vacation {}".format(self.vacation))
            except:
                pass
        
        # Temp update thread.
        def updateTemp():
            while self.stopNow == 0:
                self.updateTemp()
                time.sleep(self.updatePeriodS)
        self.updateTempThread = Thread(target=updateTemp, args=(), group=None)
        self.updateTempThread.daemon = True
        logging.info("Starting temp update thread")
        if doStart: self.updateTempThread.start()
        
        # Display event loop thread.
        logging.info("Starting display thread")
        self.display.startLoop(self)
        
        # Schedule thread
        def doSchedule():
            schedule.openAndRun(self)
        self.scheduleThread = Thread(target=doSchedule, args=(), group=None)
        self.scheduleThread.daemon = True
        logging.info("Starting schedule thread")
        
        # List image timer:
        def doListImages():
            self.listAllImages()
            # If successful: redo it in self.listImagePeriodS seconds
            # If not, try again very soon!
            if len(self.allImages): Timer(self.listImagePeriodS, doListImages, ()).start()
            else: Timer(60, doListImages, ()).start()
        Timer(10, doListImages, ()).start()
        if doStart: self.scheduleThread.start()
        
        def readOutsideTemp():
            while self.stopNow == 0:
                try:
                    Str = urllib2.urlopen("http://hottub.mooo.com/airTemp",timeout=3).read()
                    Dict = json.loads(Str)
                    self.outsideTemp = Dict['outsideTemperature']
                    self.outsideHum = Dict['humidity']
                    self.maxAirTemp = Dict['maxAirTemp']
                    self.minAirTemp = Dict['minAirTemp']
                    Str = urllib2.urlopen("http://lightsjl.mooo.com/_getData",timeout=3).read()
                    Dict = json.loads(Str)
                    if self.lightOn != Dict['lightStatus']:
                        self.lightOn = Dict['lightStatus']
                        self.drawButtons()
                    time.sleep(10)
                except:
                    logging.warning("Error in readoutsideTemp()")
                    pass
        self.outsideTempThread = Thread(target=readOutsideTemp, args=(), group=None)
        self.outsideTempThread.daemon = True
        self.outsideTempThread.start()
        logging.info("Starting outside temp thread")
        
        logging.info("Drawing")
        self.draw()
        logging.info("Done")
    
    def listAllImages(self):
        self.allImages = []
        # First of, list all dirs!
        try:
            for dirpath, dirnames, filenames in os.walk(self.imageDir):
                break
            else: 
                logging.info("NO IMAGE FOUND")
                return
            if len(dirnames) == 0:
                # try to mount the image directory.
                logging.info('Attemping to mount {}'.format(self.imageDir))
                os.system('mount -t cifs -o password='' //192.168.1.110/Images {}'.format(self.imageDir))
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
            logging.error("ERROR DURING SCANNING")
        logging.info("{} images found".format(len(self.allImages)))
        
    def updateImage(self,doit=0):
        if (time.time() - self.lastImageChangeTime > self.imageChangePeriodS and len(self.allImages) and self.showImage) or doit:
            # This can fail because we have another thread that could update allImages from under us.
            try:
                if self.imageIdx >= len(self.allImages): self.imageIdx = 0
                self.imagePath = self.allImages[self.imageIdx]
                self.lastImageChangeTime = time.time()
                if self.showImage: self.draw()
            except:
                logging.warning("EXCEPTION DURING IMAGE UPDATE")
            self.imageIdx += 1
        
    def updateState(self):
        tempLow = self.roomTemp <= self.targetTemp - self.heaterToggleDeltaTemp 
        tempHigh = self.roomTemp >= self.targetTemp + self.heaterToggleDeltaTemp

        if self.state == state_off:
            if tempLow:
                self.heaterToggleCount += 1
                if self.heaterToggleCount >= self.heaterToggleMinCount:
                    logging.info("Turning heater on")
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
                    logging.info("Turning heater off")
                    # Temp reached turn heater off
                    self.heaterOn = 0
                    self.state = state_off
                    self.heaterToggleCount = 0
            if time.time()-self.lastTurnOnTime > self.maxContinuousOnTimeMin*60:
                # Heater on for too long
                logging.info("Turning heater off, too long")
                self.heaterOn = 0
                self.state = state_on_too_long
            if time.time()-self.lastTurnOnForPause  > self.timeBeforePauseMin*60:
                # Take a break
                logging.info("Turning heater off, Taking a break")
                self.heaterOn = 0
                self.state = state_pausing
                self.pauseTime = time.time()
        elif self.state == state_pausing:
            if time.time()-self.pauseTime > self.pauseLengthMin*60:
                logging.info("Turning heater on, from break")
                self.heaterOn = 1
                self.state = state_on
                self.lastTurnOnForPause = time.time()
        elif self.state == state_on_too_long:
            if tempHigh:
                logging.info("Temp high enough, resuming normal state")
                self.state = state_off
        if self.showImage == 0 and time.time() > self.lastIdleTime + self.timeBeforeImage and len(self.allImages):
            self.showImage = 1
            self.showHotTub = 0
            self.hotTubControl.doUpdate=0
            self.draw()
            
        #logging.info("{} Last turn on time: {:.0f}s ago".format(stateStr[self.state],time.time()-self.lastTurnOnTime))
        #logging.info("pause time {:.0f}s ago -- last turn on for pause {:.0f}s ago".format(time.time()-self.pauseTime,time.time()-self.lastTurnOnForPause))
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
        if self.heaterOn and time.time()-self.lastTurnOnTime > self.maxContinuousOnTimeMin*60:
            self.heaterOn = 0
            self.state = state_on_too_long
        #logging.info("{} Last turn on time: {:.0f}s ago".format(stateStr[self.state],time.time()-self.lastTurnOnTime)),
        if self.heaterToggleCount >= self.heaterToggleMinCount: self.heaterToggleCount = self.heaterToggleMinCount
        GPIO.output(self.relayGPIO,self.heaterOn)

    def close(self):
        logging.info("Closing Heater Control")
        GPIO.output(self.relayGPIO,0)
        self.stopNow = 1
        self.display.close()

    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        if self.targetTemp < 50: self.targetTemp = 50
        if self.targetTemp > 74: self.targetTemp = 74
        self.heaterToggleCount = 0
        self.showTarget()
        
    def onTempOff(self):
        self.setTargetTemp(50)
        logging.info("TEMP OFF")
        
    def writeStatus(self):
        with open(self.statusFile,'w') as f:
            json.dump({'holding':self.holding,'targetTemp':self.targetTemp,'vacation':self.vacation},f)

    def onRun(self):
        self.holding = 0
        schedule.redoSchedule()
        logging.info("RUN")
        self.writeStatus()

    def onHold(self):
        logging.info("HOLD")
        self.holding = 1-self.holding
        self.drawButtons()
        self.writeStatus()
        
    def onHotTub(self):
        self.showHotTub = 1
        self.hotTubControl.doUpdate=1
        self.draw()
        return

    def onVacation(self):
        self.vacation = 1-self.vacation
        schedule.vacation = self.vacation
        self.drawButtons()
        logging.info("VACATION")
        self.writeStatus()
        
    def onLightOn(self):
        logging.info("ON LIGHT ON %d",self.lightOn)
        self.lightOn = 1-self.lightOn
        if self.lightOn:
            Dict = json.loads(urllib2.urlopen("http://lightsjl.mooo.com/_LightOn",timeout=3).read())
        else:
            Dict = json.loads(urllib2.urlopen("http://lightsjl.mooo.com/_LightOff",timeout=3).read())
        logging.info("URL RETURN %s",Dict)
        self.lightOn = Dict["lightStatus"]
        self.drawButtons()
        logging.info("Light on: %d",self.lightOn)

    def incTargetTemp(self,inc):
        self.setTargetTemp(self.targetTemp + inc)

    def onTouch(self,s,down):
        # print s.x,s.y,down
        if self.showImage:
            if down and self.waitForUp: return
            if s.x < 100 and s.x > 0:
                # print "PREVIOUS IMAGE"
                self.imageIdx -= 2
                self.updateImage(doit=1)
                self.waitForUp = 1
                return
            elif s.x>0:
                self.showImage = 0
                self.draw()
                self.showUptime()
                self.waitForUp = 1
                return
        if down:
            self.buttonPressed = self.display.findHit(s)
        else:
            self.lastIdleTime = time.time()
        if s.x < 40 and s.y < 40 and s.x>0 and s.y > 0: 
            os.system('sudo reboot now')
        if down and self.waitForUp: return
        if self.buttonPressed > -1 and down:
            #logging.info("Heater control button: {}".format(self.buttonPressed))
            def drawButtons(buttonPressed=-1):
                if not self.showHotTub:
                    self.drawButtons(highlightButton=buttonPressed)
                else:
                    self.hotTubControl.drawButtons(highlightButton=buttonPressed)
            drawButtons(self.buttonPressed)
            if self.buttonPressed in [0,1]: Timer(.3, drawButtons, ()).start()
            if not self.showHotTub:
                if self.buttonPressed == 0: self.onTempOff()
                if self.buttonPressed == 1: self.onRun()
                if self.buttonPressed == 2: self.onHold()
                if self.buttonPressed == 3: self.onLightOn()
                if self.buttonPressed == 4: self.onVacation()
                if self.buttonPressed == 5: self.onHotTub()
            else:
                self.hotTubControl.onButton(self.buttonPressed)
            self.waitForUp = 1
        if self.buttonPressed == -1:
            if down:
                inc = 5 if s.x > self.display.xSize - 50 else 1
                if s.y > .35* self.display.ySize: self.incTargetTemp(-inc)
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

    def showTarget(self):
        if self.showImage or self.showHotTub: return
        self.display.make_label("Target  {}F".format(self.targetTemp), self.display.xSize / 2, 0, 40, dc.ngreen)
        self.display.make_label("Out. {}F ({:.0f}%)".format(self.outsideTemp,self.outsideHum), self.display.xSize / 2, 40, 30, dc.nblue)
        self.display.make_label("Max {}F Min {}F".format(self.maxAirTemp,self.minAirTemp), self.display.xSize / 2, 65, 30, dc.nblue)

    def drawButtons(self,highlightButton=-1):
        if self.showImage or self.showHotTub: return
        buttX=80
        buttY=50
        margin=10
        startX = margin
        colors = [dc.nocre]*10
        if highlightButton != -1: colors[highlightButton] = dc.nred
        self.display.make_button("Off",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[0])
        startX += buttX+margin
        self.display.make_button("Run",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[1])
        startX += buttX+margin
        if self.holding: colors[2] = dc.nred
        self.display.make_button("Hold",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[2])
        startX += buttX+margin
        if self.lightOn: colors[3] = dc.nred
        self.display.make_button("Light",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[3])
        if self.vacation: colors[4] = dc.nred
        startX += buttX+margin
        self.display.make_button("Vac",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[4])
        
        startX = margin + 4*(buttX+margin)
        self.display.make_button("HT",startX,self.display.ySize-2*buttY-2*margin, buttX, buttY, colors[5])
        startX += buttX+margin
        
        
    def showRoomTemp(self,):
        if self.showImage or self.showHotTub: return
        X,Y,R=120,120,100
        if self.celcius: roomTemp = (self.roomTemp - 32) / 1.8
        else: roomTemp = self.roomTemp
        # self.display.screen.fill(dc.black, rect=pygame.Rect(X-R, Y-R, 2*R, 2*R))
        self.display.make_circle("{:.1f}".format((roomTemp)), X, Y, R, dc.nred)
        self.display.make_label("Humidity {:.0f}%".format(self.humidity),X-65,Y+38,30,dc.nteal)

    def draw(self,highlightButton=-1):
        if self.showImage:
            def finalCheck():
                return self.showImage
            self.display.displayJPEG(self.imagePath,finalCheck)
            return
        if self.showHotTub:
            self.hotTubControl.draw()
            return
        self.display.allButtons = []
        self.display.screen.fill(dc.black)
        self.drawButtons(highlightButton)
        self.showRoomTemp()
        self.showTarget()
        self.display.rectList = [[0,0,self.display.xSize,self.display.ySize]]
        # JEAN NOT NEEDED
        #self.display.update()

    def showHeater(self):
        if self.showImage or self.showHotTub: return
        self.display.make_disk(self.display.xSize-20,self.display.ySize-30,10,dc.nteal if not self.heaterOn else dc.nred)
        
    def updateTemp(self):
        humidity, curTemp = Adafruit_DHT.read_retry(self.sensor, self.sensorPin)
        if curTemp is None or humidity >= 100:
            logging.info("Failed to read temp")
            return
        curTemp += self.roomTempAdjust
        self.tempHistory = np.roll(self.tempHistory,1)
        self.tempHistory[0]=curTemp
        prevRoomTemp = round(self.roomTemp)
        self.roomTemp = np.mean(self.tempHistory[self.tempHistory>0])
        self.humidity = np.round(humidity,decimals=1)
        self.roomTemp = self.roomTemp * 1.8 + 32
        logging.info("State: {} -- Room temp {:.2f}C {:.2f}F Hum: {}".format(stateStr[self.state],curTemp,self.roomTemp,self.humidity))
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
        if self.showImage or self.showHotTub: return
        # get uptime from the linux terminal command
        from subprocess import check_output
        import re
        uptime = check_output(["uptime"])
        uptime = re.sub('[\d]+ user[s]*,.*load(.*),.*,.*', 'load\\1', uptime).strip()
        # self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 50, 300, 40))
        self.display.make_label(uptime, self.display.xSize / 2, 95, 16, dc.nblue)
        #self.display.screen.fill(dc.black, rect=pygame.Rect(self.display.xSize / 2, 70, 300, 40))
        #self.display.make_label(self.lastMsg, self.display.xSize / 2, 70, 20, dc.nblue)
        #self.display.screen.fill(dc.black, rect=pygame.Rect(0,self.display.ySize -20, 500, 40))
        self.display.make_label(myLogger.lastMessage, 0, self.display.ySize -18, 16, dc.nblue, fullLine=1)
        
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
        
