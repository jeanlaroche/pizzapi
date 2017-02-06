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

numBitToRead = 24
dataLength = 1000

bitCount = 10000
clock = [0]*dataLength
data = [0]*dataLength

def noRead(channel): pass

def printList(A):
	for val in A: print "{} ".format(val),
	print " "

def waitForClockLow():
	minReadForClockLow = 0
	while 1:
		for ii in range(minReadForClockLow):
			a = GPIO.input(clockGPIO)
			if a == 1: break
		else:
			# N null data read, we're good.
			break

def readDataBit(channel):
	global bitCount
	if bitCount >= dataLength: return
	# time.sleep(.1/40000)
	data[bitCount] = GPIO.input(dataGPIO)
	# print "{} -- {}".format(bitCount,data[bitCount])
	bitCount += 1

def readClockAndData():
	while GPIO.input(clockGPIO) == 0: pass
	startRead = 0
	ii = 0
	while 1:
		clock[ii] = GPIO.input(clockGPIO)
		# Wait for the clock to go high before you start recording.
		if startRead == 0 and clock[ii] == 0: continue;
		startRead = 1
		data[ii] = GPIO.input(dataGPIO)
		ii = ii+1
		if ii>= dataLength: break
	
def readData():
	global bitCount
	bitCount = 1000
	# Wait for clock low
	# print "Wait for clock"
	# waitForClockLow()
	# Reset the bit counter:
	bitCount = 0
	# Wait for bitCount to be numBitToRead
	# while bitCount < numBitToRead: time.sleep(0.00001)
	readClockAndData()
	# printList(clock)
	# printList(data)
	
def decodeThis(clock,data):
	decodedData = []
	ic = 0
	N = len(clock)
	while 1:
		# Go go the next clock rise
		while ic < N and clock[ic]==0: ic += 1
		# Then go to the next clock fall while checking data
		dataVal = 0
		while ic < N and clock[ic] == 1:
			if data[ic] == 1: dataVal = 1
			ic += 1
		if not ic < N: break
		decodedData.append(dataVal)
	return decodedData
	
if __name__ == "__main__":
    
	GPIO.setup(clockGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(dataGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	f = open('scope.txt','w')
	t1 = time.time()
	while 1:
		try:
			readData()
			for val in clock: f.write("{} ".format(val))
			f.write('\n')
			for val in data: f.write("{} ".format(val))
			f.write('\n')
			decodedData = decodeThis(clock,data)
			printList(decodedData)
			t2 = time.time()
			# print "Elapsed {:.3f}s".format(t2-t1)
			t1=t2
			time.sleep(.1)
		except KeyboardInterrupt: break
		
	GPIO.cleanup(clockGPIO)
	GPIO.cleanup(dataGPIO)
	
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
        
        
  

