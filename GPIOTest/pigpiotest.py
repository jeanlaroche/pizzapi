import pigpio
import time
import pdb
import readTemp as rt

# To test reading the temp using pigpio.
# I'm finding that it's quite reliable.

clockGPIO 		= 3
dataGPIO 		= 4

count = 0
data = 0
numRead = 1
readData = [0]*(21*numRead+3)
stopNow = 0
lastTick = 0
startSaving = 0

# Lifted from readTemp.py
def decode(binaryData):
	try:
		# binaryData[4] is probably the heater LED.
		heater = binaryData[4]
		binaryData[4] = 0
		# You have to go from list to tuple to be able to use the dictionary
		D1 = rt.segmentsToNum[tuple(binaryData[0:7])]
		D2 = rt.segmentsToNum[tuple(binaryData[7:14])]
		D3 = rt.segmentsToNum[tuple(binaryData[14:])]
		tempValue = 100*D1+10*D2+D3
		print "{:03d}\b\b\b\b".format(tempValue),
	except: 
		print "Bad value"

# Clock callback function
def cbf(gpio, level, tick):
	global count,readData,data,stopNow,lastTick,startSaving
	if lastTick == 0: lastTick = tick
	# Wait until there's a long gap since the last clock up, before you start saving the data.
	if tick - lastTick > 2000: startSaving = 1
	lastTick = tick
	if startSaving and count < 21*numRead:
		# Saving 'data' into the array. Data is set in the other callback function
		readData[count] = data
		count += 1
		if count >= 21*numRead: 
			stopNow = 1

# Data callback function. 
def cbf2(gpio, level, tick):
	global data
	# Simply save the current level. This is only called when level changes though.
	data = level
	
pi = pigpio.pi()

# Set the two callbacks.
cb0 = pi.callback(clockGPIO, pigpio.FALLING_EDGE, cbf)
cb1 = pi.callback(dataGPIO, pigpio.EITHER_EDGE, cbf2)

tic = time.time()
m = 0
while 1:
	try:
		while stopNow == 0: time.sleep(0.001)
		decode(readData[0:21])
		m += 1
		# Get ready for a new measurement.
		count=0
		stopNow = 0
		lastTick = 0
		startSaving = 0
	except KeyboardInterrupt:
		break

toc = time.time()
print "{} counted in {:.3f} seconds. {:.3f} reads per seconds".format(m,toc-tic,m/(toc-tic))
for jj in range(21):
	print "{} ".format(readData[jj]),
# rt.setup()
# print rt.readTemperature()