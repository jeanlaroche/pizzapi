import RPi.GPIO as GPIO
import time
import sys
import pdb
import threading
# https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/

import multiprocessing.pool
import functools

def timeout(max_timeout):
    """Timeout decorator, parameter in seconds."""
    def timeout_decorator(item):
        """Wrap the original function."""
        @functools.wraps(item)
        def func_wrapper(*args, **kwargs):
            """Closure for function."""
            pool = multiprocessing.pool.ThreadPool(processes=1)
            async_result = pool.apply_async(item, args, kwargs)
            # raises a TimeoutError if execution exceeds max_timeout
            return async_result.get(max_timeout)
        return func_wrapper
    return timeout_decorator
	
def mprint(thisSting):
# My special print function to log things.
	global lastMessage
	lastMessage = thisSting
	print(thisSting)
	
'''
'''
GPIO.setmode(GPIO.BCM)
clockGPIO 		= 24	# GPIO used to read the clock line
dataGPIO 		= 25	# GPIO used to read the data line
buttonGPIO		= 18	# GPIO used to control the temperature button.
heartBeatGPIO	= 12	# GPIO used to show a heart beat when reading temp.
buttonOn 		= 1		# GPIO Value to simulate a button press
buttonOff 		= 0		# GPIO value to simulate a button release. 

minTemp 		= 80	# Minimum settable temperature
maxTemp 		= 104 	# Maximum settable temperature

# These values can be read.
temperatureVal			=	10 # Current tub temperature
setTemperatureVal		=	10 	# Current set temperature, internal to Hot Tub
targetTemperatureVal	=	10 	# Target set temperature, what we'd like to set it to.
heaterVal 				=   0   # Current status of tub heater

isAdjustingTemp			=   0   # Flag indicating the tub is in temp adjusting mode.

dataLength 		= 1000		# How many samples we're reading each time we want to read the temp.
lastMessage 	= "All OK"	# Last printed output. Useful for logging or debugging.
fakeIt 			= 0 		# Set to one to fake function.

def setup():
	GPIO.setup(clockGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(dataGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(buttonGPIO, GPIO.OUT)
	GPIO.output(buttonGPIO,buttonOff)
	GPIO.setup(heartBeatGPIO, GPIO.OUT)
	GPIO.output(heartBeatGPIO,buttonOff)
	
def init():
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal
	# Read the tub current temp, heater status, and set temp.
	if not fakeIt:
		temperatureVal,heaterVal = readTemperature()[1:3]
		setTemperatureVal = readSetTemperature()
		targetTemperatureVal = setTemperatureVal
	
def tearDown():
	GPIO.cleanup(clockGPIO)
	GPIO.cleanup(dataGPIO)
	GPIO.cleanup(buttonGPIO)
	GPIO.cleanup(heartBeatGPIO)

def printList(A,f=0):
	if not f:
		for val in A: print("{} ".format(val)),
		print(" ")
	else:
		for val in A: f.write("{} ".format(val))
		f.write('\n')

def readBinaryData():
# Function to read the bit stream coming from the motherboard. Samples the clock and data lines, and
# returns two array of 1/0 values. 
	startRead = 0
	ii = 1
	clock = [0]*dataLength
	data = [0]*dataLength
	while (1):
		# Make sure you have at least 1000 zero clocks.
		head = 0;
		while GPIO.input(clockGPIO) == 0: head += 1
		if head > 1000: break
	# Make sure you have NOTHING here that might take any time, or you'll miss
	# reading the first clock and data samples. Here, I'm reading the first data since the clock
	# has gone high already.
	data[0] = GPIO.input(dataGPIO)
	clock[0] = 1
	# Also: don't put a for with a range() here, because that takes too much time!
	while 1:
		clock[ii] = GPIO.input(clockGPIO)
		data[ii] = GPIO.input(dataGPIO)
		ii = ii+1
		if ii>= dataLength: break
	return clock,data,head
	# printList(clock)
	# printList(data)

# Dictionary with LED segments corresponding to numbers.
segmentsToNum = {(1,1,1,1,1,1,0):0,(0,1,1,0,0,0,0):1,(1,1,0,1,1,0,1):2,(1,1,1,1,0,0,1):3,(0,1,1,0,0,1,1):4,(1,0,1,1,0,1,1):5,(1,0,1,1,1,1,1):6,(1,1,1,0,0,0,0):7,(1,1,1,1,1,1,1):8,(1,1,1,1,0,1,1):9,(0,0,0,0,0,0,0):0}

def decodeBinaryData(clock,data):
# This reads the list of clock and data values, and extracts the series of encoded bits by detecting
# clock edges. It returns the decoded temperature value, and the flag that indicates the heater is on.
# The temperature is 0 if the display is black, and it's -1 if an error occurred.
	binaryData = []
	ic = 0
	N = len(clock)
	while 1:
		# Go go the next clock rise
		while ic < N and clock[ic]==0: ic += 1
		# Then go to the next clock fall while checking data. If any data is high during the high clock bit=1.
		dataVal = 0
		while ic < N and clock[ic] == 1:
			if data[ic] == 1: dataVal = 1
			ic += 1
			lastClockUp = ic
		if not ic < N: break
		# Clock went low, append bit
		binaryData.append(dataVal)
	avSamplePerClock = 1.0*lastClockUp/len(binaryData)
	
	# binaryData corresponds to the 3x7 segments of the temperature display! It's that simple!
	# So it's easy to decode with a dictionary. 
	tempValue,heater = -1,0
	if len(binaryData) == 21:
		try:
			# binaryData[4] is probably the heater LED.
			heater = binaryData[4]
			binaryData[4] = 0
			# You have to go from list to tuple to be able to use the dictionary
			D1 = segmentsToNum[tuple(binaryData[0:7])]
			D2 = segmentsToNum[tuple(binaryData[7:14])]
			D3 = segmentsToNum[tuple(binaryData[14:])]
			tempValue = 100*D1+10*D2+D3
		except: 
			# Exceptions occur when we don't read the bits quite correctly, once in a while.
			mprint("Wrong binary format")
	else:
		pass
		# mprint("Not enough binary data")
	
	return binaryData,tempValue,heater,avSamplePerClock

def showHeartBeat():
	GPIO.output(heartBeatGPIO,buttonOn)
	time.sleep(0.05)
	GPIO.output(heartBeatGPIO,buttonOff)

# @timeout(1.0)  # if execution takes longer than expected raise a TimeoutError
# This poses a problem when this is called by the server on a timer.
def readTemperature(waitForNonZeroTemp = 0, updateTempVal = 0):
# Reads the temperature. If waitForNonZeroTemp is 1, does not return until a non-zero temp is read (i.e.,
# the display was actually showing some temperature)
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal, fakeIt
	GPIO.output(heartBeatGPIO,buttonOn)
	if fakeIt:
		time.sleep(0.05)
		GPIO.output(heartBeatGPIO,buttonOff)
		return [0,temperatureVal,1,0]
	while 1:
		clock,data,head = readBinaryData()
		binaryData,tempValue,heater,avSampPerClock = decodeBinaryData(clock,data)
		if not tempValue == -1 and (tempValue > 0 or waitForNonZeroTemp == 0): break
	heaterVal = heater
	if updateTempVal: temperatureVal = tempValue
	GPIO.output(heartBeatGPIO,buttonOff)
	return binaryData,tempValue,heater,avSampPerClock

# @timeout(1.5)  # if execution takes longer than expected raise a TimeoutError
def isDisplayBlinking():
	# Read the temperature for about 1 seconds and verify that we see some 0 values there.
	# Also returns the read temperature. If the return is 0, the display was blank the whole time.
	noDisp = 0
	tempValue = 0
	for ii in range(10):
		# Read the temp, count how many 0 values we're getting.
		tVal = readTemperature()[1]
		# mprint ("TVal = {}".format(tVal))
		if tVal == 0: noDisp += 1
		else: tempValue = tVal
		time.sleep(.1)
	return noDisp > 3,tempValue

def pressTempAdjust():
# Simulate pressing the temp adjust button by temporarily toggling a GPIO output.
	mprint ("PRESSING BUTTON")
	GPIO.output(buttonGPIO,buttonOn)
	time.sleep(.05)
	GPIO.output(buttonGPIO,buttonOff)
	time.sleep(.05)

	
def readSetTemperature():
# This reads the temperature the tub is set at, by pressing the set button
# and reading the temp.
	# See if you're already blinking, just in case.
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal, fakeIt
	if fakeIt: return setTemperatureVal
	isBlinking,tempValue = isDisplayBlinking()
	if isBlinking: 
		mprint("Already blinking")
		setTemperatureVal = tempValue;
		return tempValue
	# Press the temp adjust button
	pressTempAdjust()
	isBlinking,tempValue = isDisplayBlinking()
	if not isBlinking:
		mprint ("Error: temp button pressed but display does not blink")
		return -1
	setTemperatureVal = tempValue;
	return tempValue
	
def incSetTemperature(delta):
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal
	prevTargetTemperatureVal = targetTemperatureVal
	if targetTemperatureVal < maxTemp and delta > 0: 
		targetTemperatureVal += delta
	if targetTemperatureVal > minTemp and delta < 0: 
		targetTemperatureVal += delta 
	if not prevTargetTemperatureVal == targetTemperatureVal and isAdjustingTemp == 0:
		t = threading.Thread(target=setTemperature)
		t.daemon = True
		t.start()
	return
	
def setTemperature():
# Set the hot tub temperature, by pressing the button repeatedly while reading the set temp.
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal, isAdjustingTemp
	if isAdjustingTemp: return
	# First of, get into blinking mode
	isAdjustingTemp = 1
	setTemperatureVal = readSetTemperature()
	set0 = setTemperatureVal
	# Now press the temp adjust button repeatedly until the temp reaches the desired value
	for i in range(60):
		if setTemperatureVal == targetTemperatureVal: break
		# Press button
		pressTempAdjust()
		# Read the temp, setting waitForNonZeroTemp to 1 to avoid reading while the display is off
		setTemperatureVal = readTemperature(waitForNonZeroTemp = 1)[1]
		mprint ("Setting temp, i = {}, target = {}, read = {}".format(i,targetTemperatureVal,setTemperatureVal))
		if setTemperatureVal > set0 and targetTemperatureVal < set0 : 
			mprint("PAUSE to go DOWN")
			time.sleep(5)
			set0 = setTemperatureVal
		if setTemperatureVal < set0 and targetTemperatureVal > set0 : 
			mprint("PAUSE to go UP")
			time.sleep(5)
			set0 = setTemperatureVal
		time.sleep(.6)
	else:
		# This didn't work for some reason.
		mprint ("Could not set the temp! Last read temp: {}".format(setTemperatureVal))
		isAdjustingTemp = 0
		return
	isAdjustingTemp = 0
	mprint ("Successfully set the target temp")
	
def selfTestNoBlock():
	t = threading.Thread(target=selfTest)
	t.daemon = True
	t.start()
	
def selfTest():
	global temperatureVal, setTemperatureVal, targetTemperatureVal, heaterVal, isAdjustingTemp
	# First, check reading temp.
	mprint ("Reading temp")
	time.sleep(1)
	tempValue,heater = readTemperature()[1:3]
	mprint ("Temp {} and heater {}".format(tempValue,heater))
	time.sleep(1)
	pdb.set_trace()
	# Read the set temp:
	mprint ("Reading set temp")
	time.sleep(1)
	tempValue = readSetTemperature()
	mprint ("Set Temp is {}".format(tempValue))
	time.sleep(4)
	# Read the set temp:
	mprint ("Setting temperature to 98")
	time.sleep(1)
	targetTemperatureVal = 98
	setTemperature()
	time.sleep(1)
	
if __name__ == "__main__":
	setup()
	selfTest()
	sys.exit(0)
	# f = open('scope.txt','w')
	t1 = time.time()
	pressTempAdjust()
	while 1:
		try:
			binaryData,tempValue,heater,avSampPerClock = readTemperature()
			# printList(binaryData)
			# printList(binaryData,f)
			mprint ("Data {:} -- Heater: {} -- Av. samp. per clock {:.2f}".format(tempValue,heater,avSampPerClock))
			t2 = time.time()
			# print "Elapsed {:.3f}s".format(t2-t1)
			t1=t2
			time.sleep(.1)
		except KeyboardInterrupt: break
		except multiprocessing.TimeoutError:
			mprint ("Time out error!")
			break
	tearDown()
	
