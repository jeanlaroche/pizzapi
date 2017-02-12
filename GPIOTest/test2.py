import time
import pdb

# Function to evaluate the sampling rate for reading GPIOs.
# Using either RPi or pigpio
# sudo apt-get install pigpio python-pigpio python3-pigpio
# RUN sudo pipiod
dataLength = 100000

def testSpeed():
	import pigpio
	pi = pigpio.pi() 
	pi.set_mode( 24, pigpio.INPUT)

	time1 = time.time()
	S=0
	clock = [0]*dataLength
	for i in range(dataLength):
		aa = pi.read(24)
		clock[i]=aa
  
	time2=time.time()
	print "\nPIG{:} K reads in {:.3}s or {:.0f}kHz\n".format((i+1)/1000,time2-time1,i/(time2-time1)/1000)
	print S
	print i
	B = [ii for ii in range(len(clock)) if clock[ii] > 0]
	pdb.set_trace()

def testSpeed2():
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM) 
	GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	time1 = time.time()
	S=0
	clock = [0]*dataLength
	A = range(dataLength)
	for i in A:
		try:
			a = GPIO.input(24)
			clock[i]=a
		except KeyboardInterrupt: break
  
	time2=time.time()
	print "RPI{:} K reads in {:.3}s or {:.0f}kHz\n".format((i+1)/1000,time2-time1,i/(time2-time1)/1000)
	print i
	B = [ii for ii in range(len(clock)) if clock[ii] > 0]
	pdb.set_trace()

def testRead():
	pi.set_mode( 24, pigpio.INPUT)
	pi.set_mode( 25, pigpio.INPUT)
	clock = [0]*dataLength
	data = [0]*dataLength
	while (1):
		# Make sure you have at least 1000 zero clocks.
		head = 0;
		while pi.read(24) == 0: head += 1
		if head > 200: break
	print "got at least 1000 zeros"
	data[0] = pi.read(25)
	clock[0] = 1
	ii = 1
	# Also: don't put a for with a range() here, because that takes too much time!
	while 1:
		clock[ii] = pi.read(24)
		data[ii] = pi.read(25)
		ii = ii+1
		if ii>= dataLength: break
	

def testRead2():
	pi.set_mode( 24, pigpio.INPUT)
	pi.set_mode( 25, pigpio.INPUT)
	clock = [0]*dataLength
	data = [0]*dataLength
	while pi.read(24)==0: pass
	ii = 1
	while 1:
		clock[ii] = pi.read(24)
		data[ii] = pi.read(25)
		ii = ii+1
		if ii>= dataLength: break
	pdb.set_trace()

testSpeed()
exit(1)
print "Don't forget to start the deamon sudo pigpiod"
import pigpio
pi = pigpio.pi()
pi.set_mode( 24, pigpio.INPUT)
pi.set_mode( 25, pigpio.INPUT)


# status = pi.bb_serial_read_open(24, 200000, 1)
# time.sleep(.9)
# (count, data) = pi.bb_serial_read(24)
# status = pi.bb_serial_read_close(24)


pi.set_mode( 12, pigpio.OUTPUT)
while 1:
	try:
		for i in range(255):
			time.sleep(.002)
			pi.set_PWM_dutycycle(12,i) 
		for i in range(255):
			time.sleep(.002)
			pi.set_PWM_dutycycle(12,255-i) 
	except KeyboardInterrupt: break

pdb.set_trace()

testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
testSpeed()
testSpeed2()
