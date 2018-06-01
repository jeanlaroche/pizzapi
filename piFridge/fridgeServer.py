import pigpio
from struct import unpack
import time
import json
import os
import threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger
from flask import Flask, render_template, request, jsonify, send_from_directory
from BaseClasses.utils import myTimer
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

tempGPIO = 18
humiGPIO = 19

class FridgeControl(Server):
    
    temp = 0
    humi = 0
    targetTemp = 52
    targetHumi = 70
    tempDelta = 3
    humiDelta = 5
    
    fridgeStatus = 0
    humidiStatus = 0
    
    jsonFile = '.params.json'
    
    def __init__(self):
        myLogger.setLogger('fridge.log',mode='a')
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
        self.timerThread.start()
        
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
                time.sleep(0.010)
        # print "Elapsed: {:.0f}ms".format(1000*(time.time()-t0))
        nn,data = self.pi.i2c_read_device(self.am_handle,8)
        #print nn,data[0],data[1]
        # I'm not sure why I need to mask the top bit of data[0]... 
        if nn != 8 or data[0]&0x7F != 0x03 or data[1] != 0x04:
            return None,None
        temp = unpack('>h',data[4:6])[0]
        temp = 32+1.8*temp/10.
        humi = unpack('>h',data[2:4])[0]
        humi = humi/10.
        # print "Temp {} Humi {}".format(temp,humi)
        return temp,humi
        
    def regulate(self):
        temp,humi = self.read_SHT()
        temp1,humi1 = self.read_AM()
        logging.info("T1 %.2f T2 %.2f H1 %.1f H2 %.1f",temp,temp1,humi,humi1)
        if temp != None and humi != None:
            self.temp,self.humi = temp,humi
        #logging.info("temp: %.2f humid %.2f%%",self.temp,self.humi)
        if self.temp < self.targetTemp - self.tempDelta:
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
        self.pi.write(tempGPIO,self.humidiStatus)
        self.pi.write(humiGPIO,self.humidiStatus)

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
    fc.setTargetTemp(70)
    fc.setTargetHumi(40)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)

    time.sleep(10)
    # for ii in range(100):
        # temp,humi = fc.read_SHT()
        # print "Temp: {:.2f}F Humi {:.2f}%".format( temp, humi)
    fc.stop()
    time.sleep(1)
