import readTemp as rt
import time
import re
import datetime
import pdb

schedule = {}
todo = {}

# Per kWh cost in dollars.
winLoCost 				=	0.20	# Low rate in winter.
winHiCost 				=	0.22	# High rate in winter.
sumLoCost 				=	0.26	# Low rate in summer.
sumHiCost 				=	0.36	# High rate in summer.
startHiHour				= 	16		# High cost starts at 4pm
endHiHour				= 	21		# High cost ends at 9pm
summerMonths 			= 	[6,7,8,9]

lastTempVal				= 	-1 	# Last read temp
lastHeaterVal			= 	-1 	# Last heater value
lastHeaterTime			= 	0	# Time at last heater change
fileUpdated				=	1	# Indicates that a new value was written to the stats file (heater only)
heaterData 				= 	[]	# Will contain pairs of [time heateron/off]
tempData 				= 	[]  # Will contain pairs of [time temp]
statsDay 				= 	0   # 0 for today, -1 for yesterday etc.
lastTempTime 			=	0 	# When the temp changes, time of the last measured previous value.

if rt.fakeIt:
	statLogFile 			= './Stats.txt'
	heaterData 				= 	[[33,0],[41,1],[42,0],[43,1],[53,0],[55,1],[62,0],[65,1],[70,0]]	# Will contain pairs of [time heateron/off]
	tempData 				= 	[[53,98],[55,97],[62,95],[65,98],[70,104]]  # Will contain pairs of [time temp]
else:
	statLogFile 			= '/home/pi/GPIOTest/Stats.txt'
statLogF				= open(statLogFile,'a',0)

def getCtime():
	# Subtracting a multiple of 24 because time.time() starts at 00:00.
	# timezone is to get the local time. I wasn't careful: 412992 isn't a whole number of weeks. Perhaps I should have use just time.time()-time.timezone() to get the dates. Actually you have to use altzone to get the DST time.
	# right.
	return (time.time()-time.altzone)/3600 - 412992 
	
def getToday():
	return(24*int(getCtime() / 24))
	
# This returns the low and high cost of one hour of heater usage.
def getCost(statsDay):
	thisDate = datetime.datetime.now()-datetime.timedelta(days=-statsDay)
	if thisDate.month in summerMonths:
		if thisDate.weekday() in [5,6]: costLow,costHigh = sumLoCost,sumLoCost
		else: costLow,costHigh = sumLoCost,sumHiCost
	else:
		if thisDate.weekday() in [5,6]: costLow,costHigh = winLoCost,winLoCost
		else: costLow,costHigh = winLoCost,winHiCost
	return costLow*rt.heaterPower,costHigh*rt.heaterPower
	
def max(a,b):
	return a if a>b else b

def min(a,b):
	return a if a<b else b
	
def printHours(hours):
	if hours < 1: return "{}'".format(int(hours*60))
	else: return "{}h{:02d}'".format(int(hours),int((hours*60)%60))

# Read the stat file, grabs the heater data, and returns what should be displayed.
def computeGraphData():
	global heaterData, tempData
	today = getToday()
	with open(statLogFile,'r') as fd:
		allLines = fd.readlines()
	# Separate and massage the heater and temp data. We need floats.
	heaterData = [line for line in allLines if line[0] == 'H']
	heaterData = [item.split()[1:3] for item in heaterData]
	heaterData = [[float(item[0]),float(item[1])] for item in heaterData]

	# For the heater we want to display steps when the heater goes from 0 to 1 or 1 to 0
	# For this, we need to duplicate each entry.
	startHour = today+statsDay*24
	endHour = today+statsDay*24+24
	
	# Extract the part of the log that correspond to the period we're interested in.
	stats = ''
	for line in allLines[-1:0:-1]:
		if not line: continue
		allFields = line.split()
		lineHour = float(allFields[1])
		# In fact, go back 4 more hours in the past.
		if lineHour > startHour - 4 and lineHour < endHour:
			stats += ' '.join([allFields[6],allFields[0],allFields[2]]+allFields[8:])+'\n'
	
	A = [item for item  in heaterData if item[0] < endHour and item[0] > startHour]
	B = [];
	for item in A:
		B.append(item[:])		# Careful! If you use item you'll get a reference, not a copy.
		B[-1][1] = 1-B[-1][1]	# Flip value.
		B.append(item[:])
	heaterTime = [item[0]-startHour for item in B]
	heaterValue = [item[1] for item in B]
	heaterUsage = 0
	heaterCost = 0
	heaterTotalUsage = 0
	
	costLow,costHigh = getCost(statsDay)
	
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
		# max(prevTime,startHour - 1) is useful because we only want to count the time within the past hour, not since
		# the last log.
		if tim > startHour and prevTime < endHour: 
			dur = min(tim,endHour) - max(prevTime,startHour)
			if tim > startHiHour and tim < endHiHour: heaterCost += dur * costHigh
			else: heaterCost += dur * costLow
			heaterUsage += dur
		heaterTotalUsage += tim - prevTime

	totTime = getCtime() - heaterData[0][0] if heaterData else 1
	heaterTotalUsage = heaterTotalUsage / totTime
	# I should have used time.time() straight with no offset but I didn't. So to get the day right, I have to re-add this.
	offset = 412992*3600
	format = '%A, %b %d'
	thisDayStr = time.strftime(format,time.gmtime(startHour*3600+offset)) if statsDay else "today"
	nextDayStr = time.strftime(format,time.gmtime(startHour*3600+offset+24*3600))
	prevDayStr = time.strftime(format,time.gmtime(startHour*3600+offset+-24*3600))
	avUsageStr = "Average usage: {} / day -- {:.1f} kWh -- {:.0f} W".format(printHours(24*heaterTotalUsage),24*heaterTotalUsage*rt.heaterPower,heaterTotalUsage*rt.heaterPower*1000)
	usageStr = "{} -- {:.1f} kWh <br> {:.0f} W -- {:.2f}$".format(printHours(heaterUsage),heaterUsage*rt.heaterPower,heaterUsage*rt.heaterPower*1000/24,heaterCost)
	return heaterTime,heaterValue,usageStr,avUsageStr,thisDayStr,prevDayStr,nextDayStr,stats

def logHeaterUse():
	global lastHeaterVal, lastTempVal, fileUpdated, lastTempTime, lastHeaterTime
	
	timeStr = time.ctime(time.time())
	curTime = getCtime()
	
	# Log a heater change in the format: FracTimeInHours new heatervalue date
	#rt.mprint("Logging heater {}".format(rt.heaterVal))
	if not lastHeaterVal == rt.heaterVal and not lastHeaterVal == -1:
		fileUpdated = 1
		if lastHeaterVal == 0:
			statLogF.write("H {:.2f} {} {}\n".format(curTime,rt.heaterVal,timeStr))
		else:
			elapsedTime = curTime - lastHeaterTime
			statLogF.write("H {:.2f} {} {} -- {} Set: {}\n".format(curTime,rt.heaterVal,timeStr,printHours(elapsedTime),rt.targetTemperatureVal))
		lastHeaterTime = curTime
	# To avoid logging the temp everytime we start.
	if lastTempVal == -1 and rt.temperatureVal: lastTempVal = rt.temperatureVal
	
	if not lastTempVal == rt.temperatureVal and rt.temperatureVal:
		# Check that the last previous temps was at least 4 minutes ago: the temp has been different for 
		# at least 4 minutes. Otherwise just wait.
		if 60*(curTime - lastTempTime) > 4:
			statLogF.write("T {:.2f} {} {}\n".format(curTime,rt.temperatureVal,timeStr))
			lastTempVal = rt.temperatureVal
	else:
		lastTempTime = curTime

	lastHeaterVal = rt.heaterVal
	
	
def readSchedule(file,verbose=0):
	global schedule, todo
	if verbose: print "Reading {}".format(file)
	with open(file,'r') as f:
		schedule = {}
		todo = {}
		for line in f.readlines():
			line = line.strip()
			if not line or line[0] == '#': continue
			# Split
			R = re.search(r'(\d+\:\d+)[,\s]+(\d+)[,\s]*(.*)',line)
			if not R and verbose:
				print "Could not parse {}, continuing".format(line)
			if not R.group(3): schedule[R.group(1)]=[R.group(2)]
			else: 
				# Parse the day field.
				if R.group(3).lower() == 'm-f': dayField = [0,1,2,3,4]
				elif R.group(3).lower() == 'we': dayField = [5,6]
				else: dayField = []
				schedule[R.group(1)]=[R.group(2),dayField]
			todo[R.group(1)] = 1
	if verbose: print "Done"
	if verbose:
		for key in schedule.keys():
			print "At {} --> {}F".format(key,schedule[key][0])

# Redo the last scheduled event.
def redoSchedule():
	thisDate = datetime.datetime.now()
	curTime = thisDate.strftime('%H:%M')
	allTimes = sorted([key for key in schedule.keys() if key <= curTime])
	if not allTimes:
		# curTime is before any of the schedule entries, redo the latest one.
		allTimes = sorted([key for key in schedule.keys() if key > curTime])
	if allTimes: 
		key = allTimes[-1]
		if len(schedule[key]) == 1 or (thisDate.weekday() in schedule[key][1]):		
			rt.mprint("Redoing schedule for = {} setting tub to {}F".format(key,schedule[key][0]))
			rt.targetTemperatureVal = int(schedule[key][0])
			rt.setTemperature()
			todo[key] = 0

def openAndRun():
	# Open the schedule file
	file = '/home/pi/GPIOTest/hottub.txt'
	print "STARTING SCHEDULE"
	if rt.fakeIt: return
	readSchedule(file,verbose=1)
	# I'm going to do it from scratch. I could use sched, but it would be a bit of a mess.
	doMidnightReset = 1
	while 1:
		# Get the current time.
		thisDate = datetime.datetime.now()
		curTime = thisDate.strftime('%H:%M')
	
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
			# Check the day of the week! Execute if there's no week day indication or the current week day is in!
			if len(schedule[curTime]) == 1 or (thisDate.weekday() in schedule[curTime][1]):
				rt.mprint("Time = {} Schedule: setting tub to {}F".format(curTime,schedule[curTime][0]))
				rt.targetTemperatureVal = int(schedule[curTime][0])
				rt.setTemperature()
				todo[curTime] = 0
		time.sleep(30)
		
if __name__ == "__main__":
	statString = computeStats()[0]
	print(statString)