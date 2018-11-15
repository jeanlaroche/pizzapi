import pigpio
import time
import logging
from BaseClasses import myLogger
from BaseClasses.utils import printSeconds

myLogger.setLogger('gate.log',dateFormat="%H:%M:%S")
GPIO = 17
pi = pigpio.pi()
pi.set_mode(GPIO, pigpio.INPUT)
pi.set_pull_up_down(GPIO, pigpio.PUD_DOWN)
prevVal = -1
while 1:
    val = pi.read(GPIO)
    # print val
    if prevVal == -1: 
        prevVal = val
        t1=time.time()
        print "Starting: val = {}".format(val)
    if val != prevVal:
        t2 = time.time()
        logging.info("Val -> %d ... Elapsed %s",val,printSeconds(t2-t1))
        t1 = t2
        if val == 1:
            logging.info("Detection")
    prevVal = val
    time.sleep(1)
   