import readTemp as rt
import time
import re
import datetime
import pdb

schedule = {}
todo = {}

def readSchedule(file):
	global schedule, todo
	print "Reading {}".format(file)
	with open(file,'r') as f:
		schedule = {}
		todo = {}
		for line in f.readlines():
			line = line.strip()
			if line[0] == '#': continue
			# Split
			R = re.search(r'(\d+\:\d+)[,\s]+(\d+)',line)
			if not R:
				print "Could not parse {}, continuing".format(line)
			schedule[R.group(1)]=R.group(2)
			todo[R.group(1)] = 1
	print "Done"
	for key in schedule.keys():
		print "At {} --> {}F".format(key,schedule[key])

def openAndRun():
	# Open the schedule file
	file = '/home/pi/GPIOTest/hottub.txt'
	print "STARTING SCHEDULE"
	if rt.fakeIt: return
	readSchedule(file)
	firstTime = 1
	# I'm going to do it from scratch. I could use sched, but it would be a bit of a mess.
	doMidnightReset = 1
	while 1:
		# Get the current time.
		thisDate = datetime.datetime.now()
		curTime = thisDate.strftime('%H:%M')
		print curTime
		if firstTime:
			# First time around, sort the times, and execute the action for the last one that should have run.
			firstTime = 0
			allTimes = sorted([key for key in schedule.keys() if key <= curTime])
			if allTimes: 
				key = allTimes[-1]
				rt.mprint("Redoing schedule for = {} setting tub to {}F".format(key,schedule[key]))
				rt.targetTemperatureVal = int(schedule[key])
				rt.setTemperature()
				todo[key] = 0
	
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
	openAndRun()