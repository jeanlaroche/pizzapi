import time
import pigpio
from struct import unpack
import sys

pi = pigpio.pi()
h = pi.i2c_open(1, 0x44)
    
def readTH(timeOutS=1):
    # I write the raw device as that's easier. This is for no clock stretching.
    pi.i2c_write_device(h, [0x24, 0x00])
    nn=0
    t0=time.time()
    # Read 6 bytes, returned as TMSB|TLSB|CRC|HMSB|HLSB|CRC
    while time.time()-t0 < timeOutS:
        nn,data = pi.i2c_read_device(h, 6)
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
    print h
    import pdb
    # pdb.set_trace()
    for ii in range(100):
        temp,humi = readTH()
        print "Temp: {:.2f}F Humi {:.2f}%".format( temp, humi)
    pi.stop()
