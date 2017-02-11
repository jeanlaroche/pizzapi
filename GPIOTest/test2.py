import time
import pdb

# Function to evaluate the sampling rate for reading GPIOs.
# Using either RPi or pigpio
# sudo apt-get install pigpio python-pigpio python3-pigpio

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

print "Don't forget to start the deamon sudo pigpiod"
pdb.set_trace()
testSpeed()
testSpeed2()

import pigpio
pi = pigpio.pi() 

status = pi.bb_serial_read_open(4, 40000, 1)
(count, data) = pi.bb_serial_read(4)
status = pi.bb_serial_read_close(4)

pi.set_mode( 4, pigpio.OUTPUT)
while 1:
	try:
		for i=range(255):
			time.sleep(.01)
			pi.set_PWM_dutycycle(4,i) 
		for i=range(255):
			time.sleep(.01)
			pi.set_PWM_dutycycle(4,255-i) 
	except KeyboardInterrupt: break

pdb.set_trace()

testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
