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
        self.handle = self.pi.i2c_open(1, 0x44)
        self.stopNow = 0
        if os.path.exists(self.jsonFile):
            with open(self.jsonFile) as f:
                data = json.load(f)
                self.targetTemp = data['targetTemp']
                self.targetHumi = data['targetHumi']
        
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
        self.pi.i2c_write_device(self.handle, [0x24, 0x00])
        nn=0
        t0=time.time()
        # Read 6 bytes, returned as TMSB|TLSB|CRC|HMSB|HLSB|CRC
        while time.time()-t0 < timeOutS:
            nn,data = self.pi.i2c_read_device(self.handle, 6)
            if nn==6: break
            time.sleep(0.1)
        if nn < 6:
            return 0.,0.
        # Convert the value using the first 2 bytes for the temp
        temp = unpack('>H',data[0:2])[0]
        # temp = -45+175*(temp/65535.)
        temp = -49+315*(temp/65535.)
        # Convert the value using the bytes 3 and 4 for the humidity
        humi = unpack('>H',data[3:5])[0]
        humi = 100.*humi/65535.
        return temp,humi
        
    def regulate(self):
        self.temp,self.humi = self.read_SHT()
        logging.info("temp: %.2f humid %.2f%%",self.temp,self.humi)
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


if __name__ == "__main__":
    fc = FridgeControl()
    fc.setTargetTemp(70)
    fc.setTargetHumi(40)
    time.sleep(10)
    # for ii in range(100):
        # temp,humi = fc.read_SHT()
        # print "Temp: {:.2f}F Humi {:.2f}%".format( temp, humi)
    fc.stop()
    time.sleep(1)
