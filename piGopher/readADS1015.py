import time
import pigpio
from struct import unpack
import sys
import numpy as np

pi = pigpio.pi()
h = pi.i2c_open(1, 0x48)
    
def getGain(chan=0):
    ''' Get the appropriate gain for the signal at the given channel'''
    for gain in range(5,0,-1):
        vals = readValues(chan,gain,40,verbose=0)[0]
        if np.max(abs(vals)) < 2047: return gain
    return 0


def readValues(chan=0,gain=1,numVals=10,verbose=0):
    '''Chan is from 0 to 3. gain is from 0 to 5 or -1 for auto
    0 = +/-6.144V
    1 = +/-4.096V
    2 = +/-2.048V
    3 = +/-1.024V
    4 = +/-0.512V
    5 = +/-0.256V
    Return is measuredVals,times,gain
    For now all channels are channel-ground (no differential input).
    '''
    if gain==-1: gain = getGain(chan)
    # The last bit is the mode, 1 for continuous, 0 for single.
    pi.i2c_write_device(h, [0x01, 0xC0+(chan<<4)+(gain<<1), 0x83])
    #Select conversion register
    pi.i2c_write_device(h, [0x00])
    t0 = time.time()
    retVals = []
    retTimes = []
    if 1:
        # This is a LOT faster. You send the i2c commands in a series. 6 means read, 2 for 2 bytes,
        # Then next 2 is for "switch combined flags on" not sure what this means.
        code = [6,2,2]*numVals
        num_read, data = pi.i2c_zip(h,code)
        for ii in range(0,numVals,2):
            value = unpack('>h',data[ii:ii+2])[0]
            value >>= 4
            #print "{:03d}".format(value)
            retVals.append(value)
            retTimes.append(time.time()-t0)
    else:
        for ii in range(numVals):
            import pdb
            num_read, data = pi.i2c_read_device(h, 2)
            #num_read, data = pi.i2c_read_i2c_block_data(h, 0, 2)
            value = unpack('>h',data[0:2])[0]
            value >>= 4
            #print "{:03d}".format(value)
            retVals.append(value)
            retTimes.append(time.time()-t0)
    t1=time.time()
    if verbose: print "{} values read in {}s or {} values per sec".format(numVals,t1-t0,numVals/(t1-t0))
    return np.array(retVals,dtype=int),np.array(retTimes),gain

if __name__ == "__main__":
    chan = int(sys.argv[1])
    gain = int(sys.argv[2])
    numVals = int(sys.argv[3])
    #ret = readValuesAutoScale(chan,numVals)
    print "Maplotlib"
    #import matplotlib.pyplot as pp
    while 1:
        ret,tim = readValues(chan,gain,numVals)[0:2]
        # print np.diff(tim)
        print "Mean {} std {}".format(np.mean(ret),np.std(ret))
        if 0:
            pp.clf()
            print "clear done"
            pp.plot(tim,ret)
            print "plot done"
            pp.draw()
            print "draw done"
            pp.show(block=False)
            print "show done"
            pp.pause(0.001)
    pi.stop()
        