import pigpio
from struct import unpack
import time
import threading
from BaseClasses.baseServer import Server
import logging
from BaseClasses import myLogger
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

tempGPIO = 18
humGPIO = 19

class FridgeControl(Server):
    
    oscFreqHz = 320*4
    pwmRange = 1024
    target = 255
    def __init__(self):
        myLogger.setLogger('fridge.log',mode='a')
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.pi.set_mode(tempGPIO, pigpio.OUTPUT)
        self.pi.set_mode(humGPIO, pigpio.OUTPUT)
        self.handle = self.pi.i2c_open(1, 0x44)
        
    def stop(self):
        self.pi.stop()
        
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


if __name__ == "__main__":
    fc = FridgeControl()
    for ii in range(100):
        temp,humi = fc.read_SHT()
        print "Temp: {:.2f}F Humi {:.2f}%".format( temp, humi)
    fc.stop()
