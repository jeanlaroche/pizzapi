import readTemp as rt
import time
import re
import datetime
import pdb

schedule = {}
todo = {}

lastTempVal				= 	-1 	# Last read temp
lastHeaterVal			= 	-1 	# Last heater value
heaterData 				= 	[]	# Will contain pairs of [time heateron/off]
tempData 				= 	[]  # Will contain pairs of [time temp]
if rt.fakeIt:
	statLogFile 			= './Stats.txt'
	heaterData 				= 	[[33,0],[41,1],[42,0],[43,1],[53,0],[55,1],[62,0],[65,1],[70,0]]	# Will contain pairs of [time heateron/off]
	tempData 				= 	[[53,98],[55,97],[62,95],[65,98],[70,104]]  # Will contain pairs of [time temp]
else:
	statLogFile 			= '/home/pi/GPIOTest/Stats.txt'
statLogF				= open(statLogFile,'a',0)

def getCtime():
	# Subtracting a multiple of 24 because time.time() starts at 00:00.
	# timezone is to get the local time.
	return (time.time()-time.timezone)/3600 - 412992 
	
def getToday():
	return(24*int(getCtime() / 24))
	
def max(a,b):
	return a if a>b else b
	
def printHours(hours):
	if hours < 1: return "{}'".format(int(hours*60))
	else: return "{}h{:02d}'".format(int(hours),int((hours*60)%60))
	
def computeStats():
	global heaterData, tempData
	with open(statLogFile,'r') as fd:
		allLines = fd.readlines()
	# Separate and massage the heater and temp data. We need floats.
	heaterData = [line for line in allLines if line[0] == 'H']
	heaterData = [item.split()[1:3] for item in heaterData]
	heaterData = [[float(item[0]),float(item[1])] for item in heaterData]
	tempData = [line for line in allLines if line[0] == 'T']
	tempData = [item.split()[1:3] for item in tempData]
	tempData = [[float(item[0]),float(item[1])] for item in tempData]
	# Current time in float hours.
	curTime = getCtime()
	# 00:00 this morning.
	today = 24*int(curTime / 24)
	# 00:00 yesterday morning.
	yesterday = today - 24
	# Stats.
	heaterPastHour = 0
	heaterToday = 0
	heaterYesterday = 0
	heater2DaysAgo = 0
	heaterTotal = 0
	for ii,[tim,heat] in enumerate(heaterData):
		# Ignore the first entry, and all entry where heat = 1 (because this means the time span until this entry
		# had heater off.
		if ii == 0 or heat == 1: continue
		# Time at previous entry, 
		prevTime = heaterData[ii-1][0]
		# This should not happen since we only log heater changes.
		if heaterData[ii-1][1] == 0 : 
			print "Weird, two consecutive heater entry with heater=0"
			continue
		# max(prevTime,curTime - 1) is useful because we only want to count the time within the past hour, not since
		# the last log.
		if prevTime > curTime - 1 : heaterPastHour += tim - max(prevTime,curTime - 1)
		if prevTime > today : heaterToday += tim - max(prevTime,today)
		if prevTime > yesterday and prevTime < today : heaterYesterday += tim - max(prevTime,yesterday)
		if prevTime > today-48 and prevTime < today-24 : heater2DaysAgo += tim - max(prevTime,today-48)
		heaterTotal += tim - prevTime
	totTime = curTime - heaterData[0][0] if heaterData else 1
	heaterTotal = heaterTotal / totTime
	statString = ["Past hour: {}".format(printHours(heaterPastHour))]
	statString.append("Since midnight: {}".format(printHours(heaterToday)))
	statString.append("Yesterday: {}".format(printHours(heaterYesterday)))
	statString.append("2 Days ago: {}".format(printHours(heater2DaysAgo)))
	return statString,heaterPastHour,heaterToday,heaterYesterday,heaterTotal

def logHeaterUse():
	global lastHeaterVal, lastTempVal
	
	timeStr = time.ctime(time.time())
	curTime = getCtime()
	
	# Log a heater change in the format: FracTimeInHours new heatervalue date
	if not lastHeaterVal == rt.heaterVal and not lastHeaterVal == -1:
		statLogF.write("H {:.2f} {} {}\n".format(curTime,rt.heaterVal,timeStr))
	
	if not lastTempVal == rt.temperatureVal and rt.temperatureVal:
		statLogF.write("T {:.2f} {} {}\n".format(curTime,rt.temperatureVal,timeStr))
		lastTempVal = rt.temperatureVal

	lastHeaterVal = rt.heaterVal
	
	
def readSchedule(file,verbose=0):
	global schedule, todo
	if verbose: print "Reading {}".format(file)
	with open(file,'r') as f:
		schedule = {}
		todo = {}
		for line in f.readlines():
			line = line.strip()
			if line[0] == '#': continue
			# Split
			R = re.search(r'(\d+\:\d+)[,\s]+(\d+)',line)
			if not R and verbose:
				print "Could not parse {}, continuing".format(line)
			schedule[R.group(1)]=R.group(2)
			todo[R.group(1)] = 1
	if verbose: print "Done"
	if verbose:
		for key in schedule.keys():
			print "At {} --> {}F".format(key,schedule[key])

# Redo the last scheduled event.
def redoSchedule():
	thisDate = datetime.datetime.now()
	curTime = thisDate.strftime('%H:%M')
	allTimes = sorted([key for key in schedule.keys() if key <= curTime])
	if not allTimes:
		# curTime is before any of the schedule entries, redo the latest one.
		allTimes = sorted([key for key in schedule.keys() if key > curTime],reverse=True)
	if allTimes: 
		key = allTimes[-1]
		rt.mprint("Redoing schedule for = {} setting tub to {}F".format(key,schedule[key]))
		rt.targetTemperatureVal = int(schedule[key])
		rt.setTemperature()
		todo[key] = 0

def openAndRun():
	# Open the schedule file
	file = '/home/pi/GPIOTest/hottub.txt'
	print "STARTING SCHEDULE"
	if rt.fakeIt: return
	readSchedule(file,verbose=1)
	firstTime = 1
	# I'm going to do it from scratch. I could use sched, but it would be a bit of a mess.
	doMidnightReset = 1
	while 1:
		# Get the current time.
		thisDate = datetime.datetime.now()
		curTime = thisDate.strftime('%H:%M')
		if firstTime:
			# First time around, sort the times, and execute the action for the last one that should have run.
			firstTime = 0
			redoSchedule()
	
		# Re-read the schedule file. This allows us to change the schedule without restarting. Don't read if
		# a change is occurring at this precise time, it would reset todo[]
		if not curTime in schedule.keys() : readSchedule(file)
		# Reset all the todo flags at midnight. Do that before doing the scheduling. This will allow an even scheduled at 
		# midnight to run. Make sure you only do it once of course.
		if curTime == "00:00" and doMidnightReset:
			for key in schedule.keys(): todo[key] = 1
			doMidnightReset = 0
		if curTime > "00:02": doMidnightReset = 1
		# Now run the schedules.
		if curTime in schedule.keys() and todo[curTime] == 1:
			# Execute the schedule if todo is 1 for this event.
			rt.mprint("Time = {} setting tub to {}F".format(curTime,schedule[curTime]))
			rt.targetTemperatureVal = int(schedule[curTime])
			rt.setTemperature()
			todo[curTime] = 0
		time.sleep(30)
		
if __name__ == "__main__":
	statString = computeStats()[0]
	print(statString)