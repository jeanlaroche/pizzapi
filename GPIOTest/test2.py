import time
import pdb

# Function to evaluate the sampling rate for reading GPIOs.
# Using either RPi or pigpio
def testSpeed():
	import pigpio
	pi = pigpio.pi() 
	pi.set_mode( 4, pigpio.INPUT)

	time1 = time.time()
	for i in range(10000000):
		try:
			a = pi.read(4)
		except KeyboardInterrupt: break
  
	time2=time.time()
	print "PIG{:} K reads in {:.3}s or {:.0f}kHz\n".format((i+1)/1000,time2-time1,i/(time2-time1)/1000)

def testSpeed2():
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM) 
	GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	time1 = time.time()
	for i in range(10000000):
		try:
			a = GPIO.input(4)
		except KeyboardInterrupt: break
  
	time2=time.time()
	print "RPI{:} K reads in {:.3}s or {:.0f}kHz\n".format((i+1)/1000,time2-time1,i/(time2-time1)/1000)

pdb.set_trace()
testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
