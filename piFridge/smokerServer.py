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
from lumaDisplay import Luma

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

tempGPIO = 4

class SmokerControl(Server):
    
    temp = 0
    targetTemp = 52
    tempDelta = .5
    lumaText = ''
    
    smokerStatus = 0
    lastTimeOn=0
    
    logDeltaS = 120  # Time interval in s between two data logs
    lastLogTime = 0
    totalOnTimeS = 0
    lastTotalOnTimeS = 0
    warnOnTimeS = 20*60 # Warn if smoker is on for more than this time.
    
    jsonFile = '.params.json'
    logFile = 'smoker.log'
    readErrorCnt = 0
    
    periods = [{},{'temp':120,'durMn':10,'startT':0},{'temp':150,'durMn':5,'startT':0},{'temp':175,'durMn':2,'startT':0}]
    curPeriod = 0
    runProgram = 0
    
    def __init__(self,startThread=1):
        myLogger.setLogger(self.logFile,mode='a')
        logging.info('Setting up display')
        self.luma = Luma()
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(tempGPIO, pigpio.OUTPUT)
        self.hdc_handle = self.pi.i2c_open(1, 0x40)
        self.stopNow = 0
        if os.path.exists(self.jsonFile):
            with open(self.jsonFile) as f:
                data = json.load(f)
                self.targetTemp = data['targetTemp']
                self.totalOnTimeS = data['totalOnTimeS']
                self.lastTotalOnTimeS = data['lastTotalOnTimeS']
                if 'periods' in data: self.periods = data['periods']
                else: self.writeJson()
        self.temp = self.targetTemp
        self.pi.write(tempGPIO,1-self.smokerStatus)
        
        self.timer = myTimer()
        # Timer to reset the total on time, and memorize the previous one.
        def foo():
            logging.info("Total on-time: %.0fm",self.totalOnTimeS/60.)
            self.lastTotalOnTimeS = self.totalOnTimeS
            self.totalOnTimeS=0
        self.timer.addEvent(0,10,foo,name='reset total time',params=[])
        self.timer.start()
        
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
        #self.startProgram()
        
    def writeJson(self):
        with open(self.jsonFile,'w') as f:
            json.dump({'targetTemp':self.targetTemp, 'totalOnTimeS':self.totalOnTimeS,'lastTotalOnTimeS':self.lastTotalOnTimeS, 'periods':self.periods},f)
    
    def stop(self):
        self.stopNow=1
        logging.info("Disconnecting from pigpio")
        self.pi.stop()
        
    def startProgram(self):
        def incPeriod():
            self.curPeriod += 1
            if self.curPeriod >= len(self.periods): 
                self.setTargetTemp(50)
                self.runProgram = 0
                return
            self.setTargetTemp(self.periods[self.curPeriod]['temp'])
            self.periods[self.curPeriod]['startT'] = time.time()
            delayMn = self.periods[self.curPeriod]['durMn']
            self.timer.addDelayedEvent(delayMn,incPeriod,[],'Period {}'.format(self.curPeriod+1))
        self.curPeriod = 0
        self.runProgram = 1
        incPeriod()
        
    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        self.writeJson()
        
    def incTargetTemp(self,inc):
        #logging.info("Inc temp %.0f",self.targetTemp)
        self.targetTemp += inc
        self.writeJson()
 
    def read_HDC1008(self,timeOutS=1):
        # I write the raw device as that's easier. This is for no clock stretching.
        #pdb.set_trace()
        self.pi.i2c_write_device(self.hdc_handle, [0x02, 0x10])
        self.pi.i2c_write_device(self.hdc_handle, [0x00])
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
            return -100,-100
        #pdb.set_trace()
        # Convert the value using the first 2 bytes for the temp
        temp = unpack('>H',data[0:2])[0]
        # temp = -45+175*(temp/65535.)
        temp = -40+297*(temp/65536.)
        # Convert the value using the bytes 3 and 4 for the humidity
        humi = unpack('>H',data[2:4])[0]
        humi = 100.*humi/65536.
        return temp,humi
        
    def regulate(self):
        time.sleep(0.1)
        temp_SHT,humi_SHT = self.read_HDC1008()
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
        self.pi.write(tempGPIO,self.smokerStatus)
        tt = time.time()
        if not self.runProgram:
            timeStr = time.strftime("%H:%M:%S",time.localtime())
        else:
            remainingS = self.periods[self.curPeriod]['durMn']*60 - (time.time() - self.periods[self.curPeriod]['startT'])
            timeStr = "Rem: {}".format(printSeconds(remainingS))
        prog = "P{} ".format(self.curPeriod) if self.runProgram else ""
        onOffStr = "{}Heat on".format(prog) if self.smokerStatus else "{}Heat off".format(prog)
        self.lumaText = 'Temp:   {:.1f}F\nTarget: {:.0f}F\n{}\n{}'.format(self.temp,self.targetTemp,onOffStr,timeStr)
        self.luma.printText(self.lumaText)
        # Only log the temp every self.logDeltaS seconds...
        if tt-self.lastLogTime > self.logDeltaS:
            logging.info("Time: %.0f T1 %.2f CC %d TT %.2f",tt,temp_SHT,self.smokerStatus,self.targetTemp)
            self.lastLogTime = tt
        if self.readErrorCnt > 40:
            logging.error("%d read errors detected",self.readErrorCnt)
            self.readErrorCnt = 0
        self.temp = round(self.temp,ndigits=1)

    def getData(self,full=0):
        if full:
            X,Y,TT,Log = self.getPlotData()
            uptime = self.GetUptime()
            onTime = "On time today {} -- yesterday {}".format(printSeconds(self.totalOnTimeS),printSeconds(self.lastTotalOnTimeS))
        else:
            X,Y,TT,Log = [],[],[],[]
            uptime,onTime = '',''
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
            R = re.search('Time:\s+(\d*)\s+T1 ([-\d\.]*)\s+CC\s+(\d)\s+TT\s+([\d\.]*)',line)
            if not R: continue
            TI,T1,CC,TT = R.group(1),R.group(2),R.group(3),R.group(4)
            TI,T1,CC,TT=int(TI),float(T1),int(CC),float(TT)
            if TI < minTime or TI < prevTI + 60: continue
            if T1 <= -100: continue
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
    return fc.Index()
        
@app.route("/getData/<int:param1>")
def getData(param1):
    return jsonify(**fc.getData(param1))
        
@app.route("/tempUp")
def tempUp():
    fc.incTargetTemp(1)
    return jsonify(**fc.getData())
    
@app.route("/tempDown")
def tempDown():
    fc.incTargetTemp(-1)
    return jsonify(**fc.getData())

@app.route("/start")
def start():
    fc.startProgram()
    return jsonify(**fc.getData())
    
fc = SmokerControl()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    time.sleep(1)
    fc.stop()
    time.sleep(1)
