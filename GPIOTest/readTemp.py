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


def noRead(channel): pass

def printList(A,f=0):
	if not f:
		for val in A: print "{} ".format(val),
		print " "
	else:
		for val in A: f.write("{} ".format(val))
		f.write('\n')

# def waitForClockLow():
	# minReadForClockLow = 0
	# while 1:
		# for ii in range(minReadForClockLow):
			# a = GPIO.input(clockGPIO)
			# if a == 1: break
		# else:
			# # N null data read, we're good.
			# break

def readData():
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

digitsToNum = {(1,1,1,1,1,1,0):0,(0,1,1,0,0,0,0):1,(1,1,0,1,1,0,1):2,(1,1,1,1,0,0,1):3,(0,1,1,0,0,1,1):4,(1,0,1,1,0,1,1):5,(1,0,1,1,1,1,1):6,(1,1,1,0,0,0,0):7,(1,1,1,1,1,1,1):8,(1,1,1,1,0,1,1):9}
int2str={0:'0',1:'1'}
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
			lastClockUp = ic
		if not ic < N: break
		decodedData.append(dataVal)
	print "Average samples per clock period: {:.2f}".format(1.0*lastClockUp/len(decodedData))
	decVal = 0
	if len(decodedData) == 21:
		try:
			# decodedData[4] is probably the heating LED.
			decodedData[4] = 0
			D1 = digitsToNum[tuple(decodedData[0:7])]
			D2 = digitsToNum[tuple(decodedData[7:14])]
			D3 = digitsToNum[tuple(decodedData[14:])]
			decVal = 100*D1+10*D2+D3
		except: pass
	
	# pdb.set_trace()
	# print "{} trailing zero clocks".format(ic-lastClockUp)
	
	return decodedData,decVal
	
if __name__ == "__main__":
    
	GPIO.setup(clockGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.setup(dataGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	f = open('scope.txt','w')
	t1 = time.time()
	while 1:
		try:
			clock,data,head = readData()
			# print "{} zero at head".format(head)
			# for val in clock: f.write("{} ".format(val))
			# f.write('\n')
			# for val in data: f.write("{} ".format(val))
			# f.write('\n')
			decodedData,decData = decodeThis(clock,data)
			printList(decodedData)
			printList(decodedData,f)
			print "Data {:}".format(decData)
			t2 = time.time()
			# print "Elapsed {:.3f}s".format(t2-t1)
			t1=t2
			time.sleep(1)
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
        
        
  

