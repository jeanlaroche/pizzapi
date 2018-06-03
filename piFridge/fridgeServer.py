import pigpio
from struct import unpack
import time
import json
import os
import re
import threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger
from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.utils import myTimer
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

tempGPIO = 4
humiGPIO = 17

class FridgeControl(Server):
    
    temp = 0
    humi = 0
    targetTemp = 52
    targetHumi = 70
    tempDelta = 1
    humiDelta = 5
    
    fridgeStatus = 0
    humidiStatus = 0
    
    logDeltaS = 60  # Time interval in s between two data logs
    lastLogTime = 0
    t1,t2,h1,h2=0,0,0,0
    
    jsonFile = '.params.json'
    logFile = 'fridge.log'
    
    def __init__(self,startThread=1):
        myLogger.setLogger(self.logFile,mode='a')
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(tempGPIO, pigpio.OUTPUT)
        self.pi.set_mode(humiGPIO, pigpio.OUTPUT)
        self.sht_handle = self.pi.i2c_open(1, 0x44)
        self.am_handle = self.pi.i2c_open(1, 0x5C)
        self.stopNow = 0
        if os.path.exists(self.jsonFile):
            with open(self.jsonFile) as f:
                data = json.load(f)
                self.targetTemp = data['targetTemp']
                self.targetHumi = data['targetHumi']
        self.temp = self.targetTemp
        self.humi = self.targetHumi
        self.pi.write(tempGPIO,1-self.fridgeStatus)
        self.pi.write(humiGPIO,1-self.humidiStatus)
        
        def mainLoop():
            while self.stopNow==0:
                try:
                    self.regulate()
                except:
                    pass
                time.sleep(2)
            logging.info('Exiting regulate loop')            
        self.timerThread = threading.Thread(target=mainLoop)
        self.timerThread.daemon = True
        if startThread: self.timerThread.start()
        
    def writeJson(self):
        with open(self.jsonFile,'w') as f:
            json.dump({'targetTemp':self.targetTemp,'targetHumi':self.targetHumi},f)
    
    def stop(self):
        self.stopNow=1
        logging.info("Disconnecting from pigpio")
        self.pi.stop()
        
    def setTargetTemp(self,targetTemp):
        self.targetTemp = targetTemp
        self.writeJson()
        
    def incTargetTemp(self,inc):
        logging.info("Inc temp %.0f",self.targetTemp)
        self.targetTemp += inc
        self.writeJson()

    def incTargetHumi(self,inc):
        logging.info("Inc humi %.0f",self.targetHumi)
        self.targetHumi += inc
        self.writeJson()

    def setTargetHumi(self,targetHumi):
        self.targetHumi = targetHumi
        self.writeJson()
        
    def read_SHT(self,timeOutS=1):
        # I write the raw device as that's easier. This is for no clock stretching.
        self.pi.i2c_write_device(self.sht_handle, [0x24, 0x00])
        nn=0
        t0=time.time()
        # Read 6 bytes, returned as TMSB|TLSB|CRC|HMSB|HLSB|CRC
        while time.time()-t0 < timeOutS:
            nn,data = self.pi.i2c_read_device(self.sht_handle, 6)
            if nn==6: break
            time.sleep(0.1)
        if nn < 6:
            logging.warning("Read error in read_SHT")
            return None,None
        # Convert the value using the first 2 bytes for the temp
        temp = unpack('>H',data[0:2])[0]
        # temp = -45+175*(temp/65535.)
        temp = -49+315*(temp/65535.)
        # Convert the value using the bytes 3 and 4 for the humidity
        humi = unpack('>H',data[3:5])[0]
        humi = 100.*humi/65535.
        return temp,humi
        
    def read_AM(self,timeOutS=1):
        t0=time.time()
        while time.time()-t0 < timeOutS:
            try:
                self.pi.i2c_write_device(self.am_handle, [0x03, 0x00, 0x04])
                break
            except:
                time.sleep(0.001)
        # print "Elapsed: {:.0f}ms".format(1000*(time.time()-t0))
        nn,data = self.pi.i2c_read_device(self.am_handle,8)
        #print nn,data[0],data[1]
        # I'm not sure why I need to mask the top bit of data[0]... 
        #if nn != 8 or data[0]&0x7F != 0x03 or data[1] != 0x04:#
        if nn != 8 or data[1] != 0x04:
            #logging.warning("Read error in read_AM")
            print "Read error"
            return None,None
        temp = unpack('>h',data[4:6])[0]
        temp = 32+1.8*temp/10.
        humi = unpack('>h',data[2:4])[0]
        humi = humi/10.
        print "Temp {} Humi {}".format(temp,humi)
        return temp,humi
        
    def regulate(self):
        temp1,humi1 = self.read_AM()
        time.sleep(0.1)
        temp,humi = self.read_SHT()
        if temp1 != None and humi1 != None:
            self.temp,self.humi = round(temp1,ndigits=1),round(humi1,ndigits=1)
            self.t1,self.t2,self.h1,self.h2=temp1,temp,humi1,humi
        #logging.info("temp: %.2f humid %.2f%%",self.temp,self.humi)
        # Making this asymetrical because there's a lot of inertia when the fridge is on.
        if self.temp < self.targetTemp - 0*self.tempDelta:
            # Turn fridge off
            if self.fridgeStatus: logging.info("Turning cooling off")
            self.fridgeStatus = 0
        if self.temp > self.targetTemp + self.tempDelta:
            # Turn fridge on
            if self.fridgeStatus == 0: logging.info("Turning cooling on")
            self.fridgeStatus = 1
        if self.humi < self.targetHumi - self.humiDelta:
            # Turn humidifier on
            if self.humidiStatus == 0: logging.info("Turning humidifier on")
            self.humidiStatus = 1
        if self.humi > self.targetHumi + self.humiDelta:
            # Turn humidifier off
            if self.humidiStatus: logging.info("Turning humidifier off")
            self.humidiStatus = 0
        self.pi.write(tempGPIO,1-self.fridgeStatus)
        self.pi.write(humiGPIO,1-self.humidiStatus)
        tt = time.time()
        # Only log the temp every self.logDeltaS seconds...
        if tt-self.lastLogTime > self.logDeltaS and temp!=None and temp1 != None and humi != None and humi1 != None:
            logging.info("Time: %.0f T1 %.2f T2 %.2f H1 %.1f H2 %.1f CC %d HH %d",tt,temp,temp1,humi,humi1,
                self.fridgeStatus,self.humidiStatus)
            self.lastLogTime = tt

    def getData(self,full=0):
        if full:
            X,Y,Z = self.getPlotData()
        else:
            X,Y,Z = [],[],[]
        uptime = self.GetUptime()+" {:.1f}F {:.1f}F {:.1f}% {:.1f}%".format(self.t1,self.t2,self.h1,self.h2)
        data = {"curTemp":self.temp,"curHumidity":self.humi,"targetHumidity":self.targetHumi,
            "targetTemp":self.targetTemp,"upTime":uptime,"fridgeStatus":self.fridgeStatus,"humStatus":self.humidiStatus,
            "X":X,"Y":Y,"Z":Z} 
        return data
    
    def getPlotData(self):
        # Read the log file, extract the temp and humidity data...
        with open(self.logFile) as f:
            allLines = f.readlines()
        X,Y,Z = [],[],[]
        minTime = time.time()-12*3600
        prevTT=0
        for line in allLines:
            if "T1" not in line: continue
            R = re.search('Time:\s+(\d*)\s+T1 ([\d\.]*)\s+T2 ([\d\.]*)\s+H1 ([\d\.]*)\s+H2 ([\d\.]*)\s+CC\s+(\d)\s+HH\s+(\d)',line)
            if not R: continue
            TT,T1,T2,H1,H2,CC,HH = R.group(1),R.group(2),R.group(3),R.group(4),R.group(5),R.group(6),R.group(7)
            TT,T1,T2,H1,H2,CC,HH=int(TT),float(T1),float(T2),float(H1),float(H2),int(CC),int(HH)
            if TT < minTime or TT < prevTT + 60: continue
            X.append((TT-minTime)/3600)
            Y.append(T2)
            Z.append(H2)
            prevTT = TT
        return X,Y,Z
        
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
    
@app.route("/humiUp")
def humiUp():
    fc.incTargetHumi(1)
    return jsonify(**fc.getData())
    
@app.route("/humiDown")
def humiDown():
    fc.incTargetHumi(-1)
    return jsonify(**fc.getData())
    
fc = FridgeControl()

# import pdb
# pi = pigpio.pi() # Connect to local Pi.
# handle = pi.i2c_open(1, 0x5C)
# t0=time.time()
# while 1:
    # try:
        # pi.i2c_write_device(handle, [0x03, 0x00, 0x04])
        # break
    # except:
        # time.sleep(0.010)
# print "Elapsed: {:.0f}ms".format(1000*(time.time()-t0))
# nn,data = pi.i2c_read_device(handle,8)
# temp = unpack('>H',data[4:6])[0]
# temp = temp/10.
# humi = unpack('>H',data[2:4])[0]
# humi = humi/10.
# print "Temp {} Humi {}".format(temp,humi)
# pdb.set_trace()
# pi.stop()

if __name__ == "__main__":
    for ii in range(100):
        t,h=fc.read_AM()
        if t != None: print t,h
        else: print "read error"
        t,h=fc.read_SHT()
        if t != None: print t,h
        else: print "read error"
        time.sleep(1)
    #app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)

    time.sleep(1)
    # for ii in range(100):
        # temp,humi = fc.read_SHT()
        # print "Temp: {:.2f}F Humi {:.2f}%".format( temp, humi)
    fc.stop()
    time.sleep(1)
