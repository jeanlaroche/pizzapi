import time
import sys
import pdb

f = open(sys.argv[1],'r')

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
	allData.append(decodedData)
	return val

allLines = f.readlines()
allData = []
for i in range(len(allLines)/2):
	clock = [int(item) for item in allLines[2*i].split()]
	data  = [int(item) for item in allLines[2*i+1].split()]
	for val in decodedData: print "{} ".format(val),
	print " "
	