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
	readSchedule(file)
	# I'm going to do it from scratch. I could use sched, but it would be a bit of a mess.
	doMidnightReset = 1
	while 1:
		# Get the current time.
		thisDate = datetime.datetime.now()
		curTime = thisDate.strftime('%H:%M')
		print curTime
		# Re-read the schedule file. This allows us to change the schedule without restarting. Don't read if
		# a change is occurring at this precise time, it would reset todo[]
		if not curTime in schedule.keys() : readSchedule(file)
		if curTime in schedule.keys() and todo[curTime] == 1:
			# Execute the schedule!
			print "Time = {} setting tub to {}F".format(curTime,schedule[curTime])
			# rt.setup()
			rt.targetTemperatureVal = int(schedule[curTime])
			rt.setTemperature()
			# rt.tearDown()
			todo[curTime] = 0
		if curTime == "00:00" and doMidnightReset:
			# Reset all the todo
			for key in schedule.keys(): todo[key] = 1
			doMidnightReset = 0
		if curTime > "00:02": doMidnightReset = 1
		time.sleep(30)
		
if __name__ == "__main__":
	openAndRun()