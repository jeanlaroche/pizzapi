import pigpio
from struct import unpack
import time
import json
import os
import re
import pdb
import threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger
from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.utils import myTimer, printSeconds
logging.basicConfig(level=logging.INFO)
#from lumaDisplay import Luma
#from readBM280 import readData

class Luma(object):
    lock = None
    def __init__(self):
        self.lock = threading.Lock()
        pass
    def printText(self,text):
        #logging.info(text)
        pass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

tempGPIO = 26
buttonGPIO1 = 15    # Top left
buttonGPIO2 = 18    # Top right
buttonGPIO3 = 17    # Bot right
buttonGPIO4 = 14    # Bot left

errorReturn = -100  # Value returned upon error

class SmokerControl(Server):
    
    temp = 0
    targetTemp = 50
    tempDelta = 1
    lumaText = ''
    
    dirty = 0           # Flag to indicate json file should be written
    
    smokerStatus = 0
    lastTimeOn=0
    
    logDeltaS = 30  # Time interval in s between two data logs
    lastLogTime = 0
    warnOnTimeS = 20*60 # Warn if smoker is on for more than this time.
    
    jsonFile = '.params.json'
    logFile = 'smoker.log'
    readErrorCnt = 0
    
    periods = [{},{'temp':120,'durMn':10,'startT':0},{'temp':150,'durMn':5,'startT':0},{'temp':175,'durMn':2,'startT':0}]
    curPeriod = 0
    runStatus = 0 # 0 is normal, 1 is run program, and 2 is programming
    
    def setButCallback(self):
        def cbf(gpio, level, tick):
            longPress = 0
            logging.debug('cfb0 %d %d %d %d',gpio, level, tick, self.runStatus)
            while self.pi.read(gpio) == 1 and longPress == 0:
                longPress = (self.pi.get_current_tick() - tick)/1.e6 > 1.
                time.sleep(0.010)
            logging.debug('cfb1')
            if gpio == buttonGPIO4 and longPress:
                # Cancel everything
                self.stopProgram()
                self.displayStuff()
                return
            if self.runStatus in [0,1]:
                # This is the regular button handling
                logging.debug('cfb2 %d',longPress)
                if longPress:
                    if gpio == buttonGPIO1:
                        self.runStatus = 2
                        self.curPeriod = 1
                        self.displayProgram()
                        return
                    if gpio == buttonGPIO2:
                        if self.runStatus==0:
                            self.startProgram()
                        else:
                            self.stopProgram()
                        self.displayStuff()
                        return
                        
                if gpio == buttonGPIO1: self.incTargetTemp(5)
                if gpio == buttonGPIO4: self.incTargetTemp(-5)
                # if self.runStatus == 1:
                    # curPeriod = self.periods[self.curPeriod]
                    # if gpio == buttonGPIO2: curPeriod['durMn'] += 10
                    # if gpio == buttonGPIO3: curPeriod['durMn'] -= 10
                    # if curPeriod['durMn'] <= 0:
                        # self.curPeriod += 1
                        # if self.curPeriod > 3:      
                            # self.stopProgram()
                        # else: self.startProgram(0)
                        # self.displayStuff()
            elif self.runStatus == 2:
                # This is the programming handling.
                if longPress: 
                    self.curPeriod = self.curPeriod + 1
                    if self.curPeriod > 3:
                        self.stopProgram()
                        self.displayStuff()
                        return
                curPeriod = self.periods[self.curPeriod]
                if gpio == buttonGPIO1: curPeriod['temp'] += 5
                if gpio == buttonGPIO4: curPeriod['temp'] -= 5
                def incMins(oneOrMinusOne):
                    if curPeriod['durMn'] < 10: curPeriod['durMn'] += oneOrMinusOne
                    else: curPeriod['durMn'] += oneOrMinusOne*10
                    curPeriod['durMn'] = max(0,curPeriod['durMn'])
                if gpio == buttonGPIO2: incMins(1)
                if gpio == buttonGPIO3: incMins(-1)
                self.writeJson()
                self.displayProgram()
                

        def setup(but):
            self.pi.set_mode(but, pigpio.INPUT)
            self.pi.set_pull_up_down(but, pigpio.PUD_DOWN)
            self.pi.set_glitch_filter(but, 10000)
            self.pi.callback(but, 0, cbf)
        setup(buttonGPIO1)
        setup(buttonGPIO2)
        setup(buttonGPIO3)
        setup(buttonGPIO4)
    
    def __init__(self,startThread=1):
        myLogger.setLogger(self.logFile,mode='a')
        logging.info('Setting up display')
        self.luma = Luma()
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(tempGPIO, pigpio.OUTPUT)
        #self.hdc_handle = self.pi.i2c_open(1, 0x40)
        self.am_handle = self.pi.i2c_open(1, 0x5C)

        self.stopNow = 0
        if os.path.exists(self.jsonFile):
            with open(self.jsonFile) as f:
                data = json.load(f)
                #self.targetTemp = data['targetTemp']
                if 'periods' in data: self.periods = data['periods']
                else: self.writeJson()
        self.temp = self.targetTemp
        self.pi.write(tempGPIO,1-self.smokerStatus)
        
        self.timer = myTimer()
        self.timer.start()
        
        # I'm finding that the temp overshoots dramatically if the heater is on for a significant amount of time.
        def pulseHeat():
            while self.stopNow==0:
                #print "status: {}".format(self.smokerStatus)
                sleepS = 2
                if self.smokerStatus == 0: 
                    #print "Writing off"
                    self.pi.write(tempGPIO,self.smokerStatus)
                else:
                # Pulse the heater if the temp is close enough to the target temp.
                    if self.temp + 35 < self.targetTemp:
                        self.pi.write(tempGPIO,self.smokerStatus)
                    else:
                        on = self.pi.read(tempGPIO)
                        toggle = 1 - on
                        sleepS = 15 if on else 5
                        #print("Toggle {}".format(toggle))
                        self.pi.write(tempGPIO,toggle)
                time.sleep(sleepS)
        self.pulseThread = threading.Thread(target=pulseHeat)
        self.pulseThread.daemon = True
        if startThread: self.pulseThread.start()         
        
        def mainLoop():
            while self.stopNow==0:
                try:
                    self.regulate()
                except Exception as e:
                    logging.error('Error in regulate: %s',e)
                    pass
                time.sleep(4)
            logging.info('Exiting regulate loop')            
        self.timerThread = threading.Thread(target=mainLoop)
        self.timerThread.daemon = True
        if startThread: self.timerThread.start()
        self.lock = threading.Lock()
        self.setButCallback()
        #self.startProgram()
        
    def writeJson(self):
        with open(self.jsonFile,'w') as f:
            json.dump({'targetTemp':self.targetTemp, 'periods':self.periods},f,indent=1)
    
    def stop(self):
        self.stopNow=1
        logging.info("Disconnecting from pigpio")
        self.pi.stop()
        
    def startProgram(self,fromScratch=1):
        self.timer.removeEvents('Period')
        def incPeriod():
            if self.curPeriod >= len(self.periods) - 1: 
                self.setTargetTemp(50)
                self.runStatus = 0
                self.curPeriod = 0
                return
            self.curPeriod += 1
            self.setTargetTemp(self.periods[self.curPeriod]['temp'])
            self.periods[self.curPeriod]['startT'] = time.time()
            delayMn = self.periods[self.curPeriod]['durMn']
            self.timer.addDelayedEvent(delayMn,incPeriod,[],'Period {}'.format(self.curPeriod+1))
        if fromScratch: 
            self.curPeriod = 0
            self.runStatus = 1
            incPeriod()
        else:
            self.curPeriod -= 1
            self.runStatus = 1
            incPeriod()
            
        
    def stopProgram(self):
        self.curPeriod = 0
        self.runStatus = 0
        self.timer.removeEvents('Period')
        self.targetTemp = 50
        
    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        self.dirty = 1
        self.displayStuff()
        
    def incTargetTemp(self,inc):
        #logging.info("Inc temp %.0f",self.targetTemp)
        self.targetTemp += inc
        self.dirty = 1
        self.displayStuff()

    def read_AM(self,timeOutS=1):
        t0=time.time()
        nn=0
        while time.time()-t0 < timeOutS:
            try:
                self.pi.i2c_write_device(self.am_handle, [0x03, 0x00, 0x04])
                nn,data = self.pi.i2c_read_device(self.am_handle,8)
                if nn != 8 or data[1] != 0x04: continue
                break
            except:
                time.sleep(0.001)
        # print "Elapsed: {:.0f}ms".format(1000*(time.time()-t0))
        #print nn,data[0],data[1]
        # I'm not sure why I need to mask the top bit of data[0]... 
        #if nn != 8 or data[0]&0x7F != 0x03 or data[1] != 0x04:#
        if nn != 8 or data[1] != 0x04:
            #logging.warning("Read error in read_AM")
            #print "Read error"
            self.readErrorCnt += 1
            return -100,-100
        temp = unpack('>h',data[4:6])[0]
        temp = 32+1.8*temp/10.
        humi = unpack('>h',data[2:4])[0]
        humi = humi/10.
        #print "Temp {} Humi {}".format(temp,humi)
        return temp,humi
        
    def read_BME280(self,timeOutS=1):
        # return 0,0
        return readData()

    def read_HDC1008(self,timeOutS=1):
        # I write the raw device as that's easier. This is for no clock stretching.
        #pdb.set_trace()
        try:
            self.pi.i2c_write_device(self.hdc_handle, [0x02, 0x10])
            self.pi.i2c_write_device(self.hdc_handle, [0x00])
        except:
            logging.warning("Read error in read_HDC1008")
            self.readErrorCnt += 1
            self.luma.printText("Error Reading\nTemp...\nTurning heat\noff")
            return errorReturn,errorReturn
        nn=0
        t0=time.time()
        # Read 6 bytes, returned as TMSB|TLSB|CRC|HMSB|HLSB|CRC
        while time.time()-t0 < timeOutS:
            nn,data = self.pi.i2c_read_device(self.hdc_handle, 4)
            if nn==4: break
            time.sleep(0.1)
        if nn < 4:
            logging.warning("Read error in read_HDC1008")
            self.readErrorCnt += 1
            return errorReturn,errorReturn
        #pdb.set_trace()
        # Convert the value using the first 2 bytes for the temp
        temp = unpack('>H',data[0:2])[0]
        # temp = -45+175*(temp/65535.)
        temp = -40+297*(temp/65536.)
        # Convert the value using the bytes 3 and 4 for the humidity
        humi = unpack('>H',data[2:4])[0]
        humi = 100.*humi/65536.
        return temp,humi
        
    def displayStuff(self,):
        if self.runStatus == 2: 
            self.displayProgram()
            return
        tt = time.time()
        if not self.runStatus:
            timeStr = time.strftime("%H:%M:%S",time.localtime())
        elif self.runStatus == 1:
            remainingS = self.periods[self.curPeriod]['durMn']*60 - (time.time() - self.periods[self.curPeriod]['startT'])
            timeStr = "Rem: {}".format(printSeconds(remainingS))
        prog = "P{} ".format(self.curPeriod) if self.runStatus else ""
        onOffStr = "{}Heat on".format(prog) if self.smokerStatus else "{}Heat off".format(prog)
        self.lumaText = 'Temp:   {:.1f}F\nTarget: {:.0f}F\n{}\n{}'.format(self.temp,self.targetTemp,onOffStr,timeStr)
        self.lock.acquire()
        self.luma.printText(self.lumaText)
        self.lock.release()

    def displayProgram(self,):
        prog = "P{} ".format(self.curPeriod)
        curPer = self.periods[self.curPeriod]
        self.lumaText = '{}\nTemp {}F\nTime {}mn'.format(prog,curPer['temp'],curPer['durMn'])
        self.lock.acquire()
        self.luma.printText(self.lumaText)
        self.lock.release()
        
    def regulate(self):
        time.sleep(0.1)
        temp_SHT,humi_SHT = self.read_AM()
        # temp_SHT,humi_SHT = self.read_BME280()
        if temp_SHT == errorReturn:
            self.smokerStatus = 0
            self.pi.write(tempGPIO,0)
            return
        self.temp = round(temp_SHT,ndigits=2)
        if self.temp < self.targetTemp - 0.5*self.tempDelta:
            # Turn heat on
            if self.smokerStatus == 0: 
                logging.info("Turning heat on %.1fF",self.temp)
                self.lastTimeOn=time.time()
            self.smokerStatus = 1
        if self.temp > self.targetTemp + .5*self.tempDelta:
            # Turn heat off
            if self.smokerStatus == 1: logging.info("Turning heat off %.2fF on for %.1f minutes",self.temp,(time.time()-self.lastTimeOn)/60.)
            self.smokerStatus = 0
        if not self.smokerStatus: self.pi.write(tempGPIO,self.smokerStatus)
        tt = time.time()
        self.displayStuff()
        # Only log the temp every self.logDeltaS seconds...
        if tt-self.lastLogTime > self.logDeltaS:
            logging.info("Time: %.0f T1 %.2f CC %d TT %.2f",tt,temp_SHT,self.smokerStatus,self.targetTemp)
            self.lastLogTime = tt
        if self.readErrorCnt > 40:
            logging.error("%d read errors detected",self.readErrorCnt)
            self.readErrorCnt = 0
        self.temp = round(self.temp,ndigits=1)
        if self.dirty: self.writeJson()
        self.dirty = 0

    def getData(self,full=0):
        X,Y,TT,Log = [],[],[],[]
        onTime = ''
        uptime = ''
        if full==1:
            X,Y,TT,Log = self.getPlotData()
            uptime = self.GetUptime()
        if full==0:
            uptime = self.GetUptime()
        data = {"curTemp":self.temp,
            "targetTemp":self.targetTemp,"upTime":uptime,"smokerStatus":self.smokerStatus,
            "X":X,"Y":Y,"TT":TT,"Log":Log,"onTime":onTime,"lumaText":self.lumaText} 
        return data
    
    def getPlotData(self):
        # Read the log file, extract the temp...
        with open(self.logFile) as f:
            allLines = f.readlines()
        X,Y,T,log = [],[],[],''
        curTime = time.time()
        curHour = time.localtime().tm_hour+time.localtime().tm_min / 60.
        minTime = curTime-4*3600
        prevTI=0
        for line in allLines:
            if "T1" not in line: continue
            R = re.search('Time:\s+(\d*)\s+T1 ([-\d\.]*)\s+CC\s+(\d)\s+TT\s+([-\d\.]*)',line)
            if not R: continue
            try:
                TI,T1,CC,TT = R.group(1),R.group(2),R.group(3),R.group(4)
                TI,T1,CC,TT=int(TI),float(T1),int(CC),float(TT)
            except Exception as e:
                print e, line, T1,CC,TT
                # import pdb
                # pdb.set_trace()
                continue
            if TI < minTime or TI < prevTI + 60: continue
            if T1 <= errorReturn: continue
            X.append(curHour+(TI-curTime)/3600)
            Y.append(T1)
            T.append(TT)
            prevTI = TI
        # For the log in the UI, don't show the temp log.
        allLines = [item for item in allLines if not "TT" in item]
        log = ''.join(reversed(allLines[-200:]))
        return X,Y,T,log
        
@app.route("/")
def Index():
    return fc.Index(pageFile='index_smoker.html')
        
@app.route("/getData/<int:param1>")
def getData(param1):
    return jsonify(**fc.getData(param1))
        
@app.route("/tempUp")
def tempUp():
    fc.incTargetTemp(5)
    print "INC"
    return jsonify(**fc.getData(-1))
    
@app.route("/tempDown")
def tempDown():
    fc.incTargetTemp(-5)
    print "DEC"
    return jsonify(**fc.getData(-1))

@app.route("/start")
def start():
    fc.startProgram()
    return jsonify(**fc.getData(-1))

@app.route("/debug")
def debug():
    logging.info("Entering debug mode")
    myLogger.setLoggingLevel(logging.DEBUG)
    logging.debug("Now in debug mode")
    return jsonify(**fc.getData(-1))
    
@app.route("/normal")
def normal():
    logging.info("Exiting debug mode")
    myLogger.setLoggingLevel(logging.INFO)
    logging.info("Now in normal mode")
    return jsonify(**fc.getData(-1))
    
@app.route("/getLog")
def getLog():
    return jsonify(log=fc.getPlotData()[-1])
    


fc = SmokerControl()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    time.sleep(1)
    fc.stop()
    time.sleep(1)
