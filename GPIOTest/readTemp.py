import RPi.GPIO as GPIO
import time
import sys
import pdb
# https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/

'''
'''
GPIO.setmode(GPIO.BCM)
clockGPIO = 24
dataGPIO = 25

dataLength = 1000

def setup():
	GPIO.setup(clockGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(dataGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	
def tearDown():
	GPIO.cleanup(clockGPIO)
	GPIO.cleanup(dataGPIO)

def printList(A,f=0):
	if not f:
		for val in A: print "{} ".format(val),
		print " "
	else:
		for val in A: f.write("{} ".format(val))
		f.write('\n')

def readBinaryData():
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
	# reading the clock and data. Here, I'm reading the first data since the clock
	# has gone high already.
	data[ii] = GPIO.input(dataGPIO)
	clock[ii] = 1
	ii = 1
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
		# Then go to the next clock fall while checking data. If data is high during the high clock bit=1.
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
			print "Wrong binary format"
			pass
	else: print "Not enough binary data"
	
	return binaryData,tempValue,heater,avSamplePerClock

def readTemperature(readNonZero = 0):
# Reads the temperature. If readNonZero is 1, does not return until a non-zero temp is read (i.e.,
# the display was actually showing some temperature)
	while 1:
		clock,data,head = readBinaryData()
		binaryData,tempValue,heater,avSampPerClock = decodeBinaryData(clock,data)
		if not tempValue == -1 and (tempValue > 0 or readNonZero): break
	return binaryData,tempValue,heater,avSampPerClock

def isDisplayBlinking():
	# Read the temperature for about 1 seconds and verify that we see some 0 values there.
	# Also returns the read temperature
	noDisp = 0
	for ii in range(10):
		binaryData,tVal,heater,avSampPerClock = readTemperature()
		if tVal == 0: noDisp += 1
		else: tempValue = tVal
		time.sleep(.1)
	return noDisp > 3,tempValue

def pressTempAdjust():
	print "PRESSING BUTTON"
	
def readSetTemperature():
# This reads the temperature the tub is set at, by pressing the set button
# and reading the temp.
	isBlinking,tempValue = isDisplayBlinking()
	if isBlinking: return tempValue
	# Press the temp adjust button
	pressTempAdjust()
	isBlinking,tempValue = isDisplayBlinking()
	if not isBlinking:
		print "Error: temp button pressed but display does not blink"
		return -1
	return tempValue
	
def setTemperature(targetTemp):
	# First of, get into blinking mode
	setTemp = readSetTemperature()
	# if setTemp == -1: return
	# Now press the temp adjust button repeatedly until the temp reaches the desired value
	for i in range(50):
		if setTemp == targetTemp: break
		# Press button
		pressTempAdjust()
		# Read the temp, setting readNonZero to 1 to avoid reading while the display is off
		q,setTemp,q,q = readTemperature(readNonZero = 1)
		time.sleep(.2)
	else:
		# This didn't work for some reason.
		print "Could not set the temp! Last read temp: {}".format(setTemp)
		return
	print "Success"
	
if __name__ == "__main__":
	setup()
	f = open('scope.txt','w')
	t1 = time.time()
	while 1:
		try:
			binaryData,tempValue,heater,avSampPerClock = readTemperature()
			# printList(binaryData)
			# printList(binaryData,f)
			print "Data {:} -- Heater: {} -- Av. samp. per clock {:.2f}".format(tempValue,heater,avSampPerClock)
			t2 = time.time()
			# print "Elapsed {:.3f}s".format(t2-t1)
			t1=t2
			time.sleep(.5)
		except KeyboardInterrupt: break
	tearDown()
	
    # # Get recording
    # values,elapsed = readGPIO(gpioNum,numMeasures,period)
    # print "Sampling rate: {:.0f} kHz\n".format(numMeasures/elapsed/1000)
    # # Output values to file.
    # with open('scope.txt','w') as f:
      # for line in values:
        # f.write("{:.1f} ".format(float(line[0])))
        # for val in line[1:]:
          # f.write("{} ".format(val))
        # f.write('\n')
        
        
  

